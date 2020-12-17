from confluent_kafka import Producer
import logging

from quart import request, make_response, jsonify
from urllib.parse import urlparse

import os
import requests

from flowlib.quart_app import QuartApp
from flowlib.etcd_utils import (
    get_etcd,
    transition_state,
)
from flowlib.constants import (
    WorkflowInstanceKeys,
    BStates,
    TRACEID_HEADER,
    flow_result,
)


KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
FORWARD_URL = os.getenv('FORWARD_URL', '')
FORWARD_TASK_ID = os.getenv('FORWARD_TASK_ID', '')

TOTAL_ATTEMPTS_STR = os.getenv('TOTAL_ATTEMPTS', '')
TOTAL_ATTEMPTS = int(TOTAL_ATTEMPTS_STR) if TOTAL_ATTEMPTS_STR else 2
FAIL_URL = os.getenv('FAIL_URL', 'http://flowd.rexflow:9002/instancefail')
FUNCTION = os.getenv('REXFLOW_THROW_END_FUNCTION', 'THROW')
WF_ID = os.getenv('WF_ID', None)
END_EVENT_NAME = os.getenv('END_EVENT_NAME', None)


kafka = None
if KAFKA_TOPIC:
    kafka = Producer({'bootstrap.servers': KAFKA_HOST})


def send_to_stream(data, flow_id, wf_id, content_type):
    headers = {
        'x-flow-id': flow_id,
        'x-rexflow-wf-id': wf_id,
        'content-type': content_type,
    }
    kafka.produce(
        KAFKA_TOPIC,
        data,
        headers=headers,
    )
    kafka.poll(0)  # good practice: flush the toilet


def make_call_(data):
    headers = {
        'x-flow-id': request.headers['x-flow-id'],
        'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
        'content-type': request.headers['content-type'],
        'x-rexflow-task-id': FORWARD_TASK_ID,
    }
    if TRACEID_HEADER in request.headers:
        headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER]
    elif TRACEID_HEADER.lower in request.headers:
        headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER.lower()]

    success = False
    for _ in range(TOTAL_ATTEMPTS):
        try:
            next_response = requests.post(FORWARD_URL, headers=headers, data=data)
            next_response.raise_for_status()
            success = True
            break
        except Exception:
            print(
                f"failed making a call to {FORWARD_URL} on wf {request.headers['x-flow-id']}",
                flush=True
            )

    if not success:
        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        requests.post(FAIL_URL, data=data, headers=headers)


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
        return jsonify(flow_result(0, ""))

    async def throw_event(self):
        data = await request.data
        if kafka is not None:
            send_to_stream(
                data,
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
                request.headers['content-type'],
            )
        if FORWARD_URL:
            make_call_(data)
        if FUNCTION == 'END':
            complete_instance(
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
                data
            )
        resp = await make_response(flow_result(0, ""))

        if TRACEID_HEADER in request.headers:
            resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER]
        elif TRACEID_HEADER.lower in request.headers:
            resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER.lower()]

        return resp

    def run(self):
        super().run()


if __name__ == '__main__':
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
