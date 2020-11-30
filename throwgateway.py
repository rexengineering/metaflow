from confluent_kafka import Producer

import asyncio
import logging
import signal
from typing import Any

from quart import Quart, request
from hypercorn.config import Config
from hypercorn.asyncio import serve
from urllib.parse import urlparse

import json
import os
import requests
from urllib.parse import urlparse

from flowlib.quart_app import QuartApp
from flowlib.etcd_utils import (
    get_etcd,
    transition_state,
)
from flowlib.constants import (
    WorkflowInstanceKeys,
    BStates,
    States,
)


KAFKA_HOST = os.environ['KAFKA_HOST']
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
FORWARD_URL = os.getenv('FORWARD_URL', '')

TOTAL_ATTEMPTS_STR = os.getenv('TOTAL_ATTEMPTS', '')
TOTAL_ATTEMPTS = int(TOTAL_ATTEMPTS_STR) if TOTAL_ATTEMPTS_STR else 2
FAIL_URL = os.getenv('FAIL_URL', 'http://flowd.rexflow:9002/instancefail')
FUNCTION = os.getenv('REXFLOW_THROW_END_FUNCTION', 'THROW')
WF_ID = os.getenv('WF_ID', None)
END_EVENT_NAME = os.getenv('END_EVENT_NAME', None)


kafka = None
if KAFKA_TOPIC:    
    kafka = Producer({'bootstrap.servers': KAFKA_HOST})


def send_to_stream(incoming_json, flow_id, wf_id):
    cp = incoming_json.copy()
    payload = incoming_json
    headers = {
        'x-flow-id': flow_id,
        'x-rexflow-wf-id': wf_id,
    }
    cp['x-flow-id'] = flow_id
    cp['x-rexflow-wf-id'] = wf_id
    kafka.produce(
        KAFKA_TOPIC,
        json.dumps(payload).encode('utf-8'),
        headers=headers,
    )
    kafka.poll(0)  # good practice: flush the toilet

def make_call_(event):
    headers = {
        'x-flow-id': request.headers['x-flow-id'],
        'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
    }
    if 'x-b3-trace-id' in request.headers:
        headers['x-b3-trace-id'] = request.headers['x-b3-trace-id']

    success = False
    for _ in range(TOTAL_ATTEMPTS):
        try:
            next_response = requests.post(FORWARD_URL, headers=headers, json=event)
            next_response.raise_for_status()
            success = True
            break
        except Exception:
            print(f"failed making a call to {FORWARD_URL} on wf {request.headers['x-flow-id']}", flush=True)

    if not success:
        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        requests.post(FAIL_URL, json=event, headers=headers)


def complete_instance(instance_id, wf_id, payload):
    assert wf_id == WF_ID, "Did we call the wrong End Event???"
    etcd = get_etcd()
    state_key = WorkflowInstanceKeys.state_key(instance_id)
    payload_key = WorkflowInstanceKeys.payload_key(instance_id)
    was_error_key = WorkflowInstanceKeys.was_error_key(instance_id)
    headers_key = WorkflowInstanceKeys.headers_key(instance_id)
    result_key = WorkflowInstanceKeys.result_key(instance_id)
    end_event_key = WorkflowInstanceKeys.end_event_key(instance_id)

    # We insist that only ONE End Event is reached. Therefore, there should
    # be no result key.
    if etcd.put_if_not_exists(result_key, payload):
        # The following code block checks to see if this WF Instance was 'restart'ed.
        # If it was `restart`ed, we should see a previous `payload` and `headers` key.
        previous_payload = etcd.get(payload_key)
        if previous_payload[0]:
            etcd.delete(headers_key)
            etcd.delete(payload_key)
            etcd.put(was_error_key, BStates.TRUE)

        # Mark the WF Instance with the name of the End Event that terminated it.
        if END_EVENT_NAME:
            etcd.put(end_event_key, END_EVENT_NAME)

        # Now, all we have to do is update the state.
        good_states = {BStates.STARTING, BStates.RUNNING}
        if not transition_state(etcd, state_key, good_states, BStates.COMPLETED):
            logging.error(
                f'Race on {state_key}; state changed out of known'
                    ' good state before state transition could occur!'
            )
            etcd.put(state_key, BStates.ERROR)
    else:
        # This means that A Bad Thing has happened, and we should transition
        # the Instance to the Error state.
        logging.error(f'Race on {state_key}; somehow we ended up at End Event twice!')
        etcd.put(state_key, BStates.ERROR)
        assert False, "somehow it was already completed?"
    return 'Great shot kid, that was one in a million!'


class EventThrowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.throw_event)

    def health_check(self):
        kafka.poll(0)
        return "May the Force be with you."

    async def throw_event(self):
        print("call to throw_event", flush=True)
        data = await request.data
        incoming_json = json.loads(data.decode())
        from pprint import pprint as pp
        pp(incoming_json)
        print("Data:", data, flush=True)
        if kafka is not None:
            send_to_stream(
                incoming_json,
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id']
            )
        if FORWARD_URL:
            make_call_(incoming_json)
        if FUNCTION == 'END':
            complete_instance(
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
                data
            )
        print("hello there, we're about to return goodness!", flush=True)
        return "For my ally is the Force, and a powerful ally it is."


    def run(self):
        super().run()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
