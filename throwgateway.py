import base64
import json
import logging
import os
import requests
import typing

from confluent_kafka import Producer
from quart import request, make_response, jsonify
from urllib.parse import urlparse

from flowlib.workflow import Workflow
from flowlib.quart_app import QuartApp
from flowlib.etcd_utils import (
    get_etcd,
    transition_state,
)
from flowlib.constants import (
    WorkflowInstanceKeys,
    BStates,
    Headers,
    flow_result,
    X_HEADER_TOKEN_POOL_ID,
)
from flowlib.config import get_kafka_config, INSTANCE_FAIL_ENDPOINT
from flowlib import token_api


KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
FORWARD_URL = os.getenv('FORWARD_URL', '')
FORWARD_TASK_ID = os.getenv('FORWARD_TASK_ID', '')

TOTAL_ATTEMPTS_STR = os.getenv('TOTAL_ATTEMPTS', '')
TOTAL_ATTEMPTS = int(TOTAL_ATTEMPTS_STR) if TOTAL_ATTEMPTS_STR else 2
FUNCTION = os.getenv('REXFLOW_THROW_END_FUNCTION', 'THROW')
WF_ID = os.getenv('WF_ID', None)
END_EVENT_NAME = os.getenv('END_EVENT_NAME', None)

KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)


kafka = None
KAFKA_CONFIG = get_kafka_config()
if KAFKA_CONFIG is not None:
    kafka = Producer(KAFKA_CONFIG)


def send_to_stream(data, flow_id, wf_id, content_type):
    headers = {
        Headers.FLOWID_HEADER: flow_id,
        Headers.WFID_HEADER: wf_id,
        'content-type': content_type,
    }
    kafka.produce(
        KAFKA_TOPIC,
        data,
        headers=headers,
    )
    kafka.poll(0)  # good practice: flush the toilet


def _shadow_to_kafka(data, headers):
    if not KAFKA_SHADOW_URL:
        return
    o = urlparse(FORWARD_URL)
    headers['x-rexflow-original-host'] = o.netloc
    headers['x-rexflow-original-path'] = o.path
    try:
        requests.post(KAFKA_SHADOW_URL, headers=headers, data=data).raise_for_status()
    except Exception:
        logging.warning("Failed shadowing traffic to Kafka")


def make_call_(data):
    headers = {
        Headers.FLOWID_HEADER: request.headers[Headers.FLOWID_HEADER],
        Headers.WFID_HEADER: request.headers[Headers.WFID_HEADER],
        'content-type': request.headers['content-type'],
        'x-rexflow-task-id': FORWARD_TASK_ID,
    }
    if Headers.TRACEID_HEADER in request.headers:
        headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
    elif Headers.TRACEID_HEADER.lower in request.headers:
        headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER.lower()]

    success = False
    for _ in range(TOTAL_ATTEMPTS):
        try:
            next_response = requests.post(FORWARD_URL, headers=headers, data=data)
            next_response.raise_for_status()
            success = True
            _shadow_to_kafka(data, headers)
            break
        except Exception:
            logging.error(
                f"failed making a call to {FORWARD_URL} on wf {request.headers[Headers.FLOWID_HEADER]}"
            )

    if not success:
        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        requests.post(INSTANCE_FAIL_ENDPOINT, data=data, headers=headers)
        headers['x-rexflow-failure'] = True
        _shadow_to_kafka(data, headers)


def complete_instance(instance_id, wf_id, payload, content_type, timer_header):
    etcd = get_etcd()
    keys = WorkflowInstanceKeys(instance_id)
    if timer_header is not None:
        # we need to release tokens, but have to be careful about it.
        # if there are multiple tokens, then release the inner-most
        # token first, and iff that token pool is DONE, release the
        # next nested token, and so on. We are completely done and the
        # flow can be completed if we exhaust the list.
        #
        # The tokens are in chrono order, so first token is oldest.
        alldone = True
        toks = timer_header.split(',')[::-1]  # sort in reverse order so newest first
        for token in toks:
            if not token_api.token_release(token):
                alldone = False
                break
        with etcd.lock(keys.timed_results):
            results = etcd.get(keys.timed_results)[0]
            if results:
                results = json.loads(results)
            else:
                results = []
            results.append({
                'token-pool-id': toks,
                'content-type': content_type,
                'end-event-name': END_EVENT_NAME,
                'payload': base64.b64encode(payload) if content_type != 'application/json' else payload.decode()
            })
            payload = json.dumps(results)
            content_type = 'application/json'
            if not alldone:
                etcd.put(keys.timed_results, payload)
                return
            # else fall through and complete the workflow instance
    assert wf_id == WF_ID, "Did we call the wrong End Event???"
    logging.info("Either no timers or all timers are done - COMPLETING")
    if etcd.put_if_not_exists(keys.result, payload):

        if not etcd.put_if_not_exists(keys.content_type, content_type):
            logging.error(f"Couldn't store content type {content_type} on instance {instance_id}.")

        # Mark the WF Instance with the name of the End Event that terminated it.
        if END_EVENT_NAME:
            etcd.put(keys.end_event, END_EVENT_NAME)

        # Now, all we have to do is update the state.
        good_states = {BStates.STARTING, BStates.RUNNING}
        if not transition_state(etcd, keys.state, good_states, BStates.COMPLETED):
            logging.error(
                f'Race on {keys.state}; state changed out of known'
                ' good state before state transition could occur!'
            )
            etcd.put(keys.state, BStates.ERROR)
    else:
        # This means that A Bad Thing has happened, and we should transition
        # the Instance to the Error state.
        logging.error(f'Race on {keys.state}; somehow we ended up at End Event twice!')
        etcd.put(keys.state, BStates.ERROR)
        assert False, "somehow it was already completed?"
    return 'Great shot kid, that was one in a million!'

class EventThrowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.throw_event)

    def health_check(self):
        return jsonify(flow_result(0, ""))

    async def throw_event(self):
        data = await request.data
        if kafka is not None:
            send_to_stream(
                data,
                request.headers[Headers.FLOWID_HEADER],
                request.headers[Headers.WFID_HEADER],
                request.headers['content-type'],
            )
        if FUNCTION == 'END':
            complete_instance(
                request.headers[Headers.FLOWID_HEADER],
                request.headers[Headers.WFID_HEADER],
                data,
                request.headers['content-type'],
                request.headers.get(X_HEADER_TOKEN_POOL_ID),
            )
        if FORWARD_URL:
            make_call_(data)
        resp = await make_response(flow_result(0, ""))

        if Headers.TRACEID_HEADER in request.headers:
            resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
        elif Headers.TRACEID_HEADER.lower in request.headers:
            resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER.lower()]

        return resp

    def run(self):
        super().run()


if __name__ == '__main__':
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
