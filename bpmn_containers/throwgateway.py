import base64
import json
import logging
import os

from confluent_kafka import Producer
from quart import request, make_response, jsonify
from urllib.parse import urlparse

from flowlib.config import get_kafka_config, INSTANCE_FAIL_ENDPOINT
from flowlib.constants import (
    WorkflowInstanceKeys,
    BStates,
    Headers,
    flow_result,
)
from flowlib.etcd_utils import (
    get_etcd,
    transition_state,
)
from flowlib.flowpost import FlowPost, FlowPostResult, FlowPostStatus
from flowlib.token_api import TokenPool
from flowlib.quart_app import QuartApp
from flowlib.workflow import Workflow


KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
FUNCTION = os.getenv('REXFLOW_THROW_END_FUNCTION', 'THROW')
WF_ID = os.getenv('WF_ID', None)
END_EVENT_NAME = os.getenv('END_EVENT_NAME', None)

SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", '')


FORWARD_TARGETS = []
if FUNCTION == 'THROW':
    FORWARD_TARGETS = json.loads(os.environ['FORWARD_TARGETS'])


kafka = None
KAFKA_CONFIG = get_kafka_config()
if KAFKA_CONFIG is not None:
    kafka = Producer(KAFKA_CONFIG)


def send_to_stream(data, flow_id, wf_id, content_type):
    headers = {
        Headers.FLOWID_HEADER: flow_id,
        Headers.X_HEADER_WORKFLOW_ID: wf_id,
        'content-type': content_type,
    }
    kafka.produce(
        KAFKA_TOPIC,
        data,
        headers=headers,
    )
    kafka.poll(0)  # good practice: flush the toilet


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
            pool = TokenPool.read(token)
            if not pool.set_complete():
                alldone = False
                logging.info(str(pool))
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
            logging.info('All timers accounted for')
            # else fall through and complete the workflow instance
    assert wf_id == WF_ID, "Did we call the wrong End Event???"
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
        if FUNCTION == 'END':
            etcd = get_etcd()
            etcd.get('healthcheck')
        return jsonify(flow_result(0, ""))

    async def throw_event(self):
        headers = dict(request.headers)
        logging.info(headers)
        try:
            data = await request.data
            if kafka is not None:
                send_to_stream(
                    data,
                    request.headers[Headers.FLOWID_HEADER],
                    request.headers[Headers.X_HEADER_WORKFLOW_ID],
                    request.headers.get(Headers.CONTENT_TYPE, 'application/json'),
                )
            print('got here', flush=True)
            if FUNCTION == 'END':
                complete_instance(
                    request.headers[Headers.FLOWID_HEADER],
                    request.headers[Headers.X_HEADER_WORKFLOW_ID],
                    data,
                    request.headers.get(Headers.CONTENT_TYPE, 'application/json'),
                    request.headers.get(Headers.X_HEADER_TOKEN_POOL_ID.lower()),
                )
            for target in FORWARD_TARGETS:
                method = target['method']
                target_url = target['target_url']
                task_id = target['task_id']
                total_attempts = int(target['total_attempts'])
                poster = FlowPost(
                    headers[Headers.X_HEADER_FLOW_ID],
                    task_id,
                    data,
                    url=target_url,
                    method=method,
                    retries=total_attempts-1,
                    shadow_url=SHADOW_URL,
                    headers=headers,
                )
                poster.send()

            resp = await make_response(flow_result(0, ""))

            if Headers.TRACEID_HEADER in request.headers:
                resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
            elif Headers.TRACEID_HEADER.lower in request.headers:
                resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER.lower()]

            return resp
        except Exception as exn:
            logging.exception("ooph", exc_info=exn)

    def run(self):
        super().run()


if __name__ == '__main__':
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
