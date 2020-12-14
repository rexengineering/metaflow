'''
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
'''
import logging

from quart import request
from urllib.parse import urlparse

from confluent_kafka import Consumer
import json
import os
import requests
import time
import sys
import traceback

from flowlib.executor import get_executor
from flowlib.quart_app import QuartApp
from flowlib import workflow
from flowlib.etcd_utils import (
    get_etcd,
)
from flowlib.constants import (
    WorkflowInstanceKeys,
    States,
    BStates,
    TRACEID_HEADER,
)


KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', '')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', '')
FORWARD_URL = os.getenv('FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.getenv('TOTAL_ATTEMPTS', '2'))
FAIL_URL = os.getenv('FAIL_URL', 'http://flowd.rexflow:9002/instancefail')

FUNCTION = os.getenv('REXFLOW_CATCH_START_FUNCTION', 'CATCH')
WF_ID = os.getenv('WF_ID', None)


kafka = None
if KAFKA_TOPIC:
    kafka = Consumer({
        'bootstrap.servers': KAFKA_HOST,
        'group.id': os.environ['KAFKA_GROUP_ID'],
        'auto.offset.reset': 'earliest'
    })
    kafka.subscribe([KAFKA_TOPIC])


class EventCatchPoller:
    def __init__(self, forward_url: str):
        self.forward_url = forward_url
        self.running = False
        self.future = None
        self.executor = get_executor()

    def start(self):
        assert self.future is None
        self.running = True
        self.future = self.executor.submit(self)

    def stop(self):
        assert self.future is not None
        self.running = False

    def get_event(self):
        msg = kafka.poll()
        return msg

    def create_instance(self, incoming_data, content_type):
        instance_id = workflow.WorkflowInstance.new_instance_id(WF_ID)
        etcd = get_etcd()
        keys = WorkflowInstanceKeys(instance_id)
        if not etcd.put_if_not_exists(keys.state, BStates.STARTING):
            # Should never happen...unless there's a collision in uuid1
            logging.error(f'{keys.state} already defined in etcd!')
            return f"Internal Error: ID {instance_id} already exists"

        etcd.put(keys.parent, WF_ID)
        first_task_response = self.make_call_(
            incoming_data,
            instance_id,
            WF_ID,
            content_type,
        )
        if first_task_response is not None:
            if not etcd.replace(keys.state, States.STARTING, BStates.RUNNING):
                logging.error('Failed to transition from STARTING -> ERROR.')
        else:
            if not etcd.replace(keys.state, States.STARTING, States.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')
        return {"id": instance_id}

    def save_traceid(self, headers, flow_id):
        trace_id = None
        if TRACEID_HEADER in headers:
            trace_id = headers[TRACEID_HEADER]
        elif TRACEID_HEADER.lower() in headers:
            trace_id = headers[TRACEID_HEADER.lower()]

        if trace_id:
            etcd = get_etcd()
            trace_key = WorkflowInstanceKeys.traceid_key(flow_id)
            with etcd.lock(trace_key):
                current_traces = []
                current_trace_resp = etcd.get(trace_key)[0]
                if current_trace_resp:
                    current_traces = json.loads(current_trace_resp.decode())
                current_traces.append(trace_id)
                current_traces = list(set(current_traces))
                etcd.put(trace_key, json.dumps(current_traces).encode())

    def make_call_(self, data, flow_id, wf_id, content_type):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
            'content-type': content_type,
        }
        for _ in range(TOTAL_ATTEMPTS):
            try:
                svc_response = requests.post(FORWARD_URL, headers=next_headers, data=data)
                svc_response.raise_for_status()
                try:
                    self.save_traceid(svc_response.headers, flow_id)
                except Exception:
                    logging.error("failed to save trace id on WF Instance")
                    traceback.print_exception(*sys.exc_info())
                return svc_response
            except Exception:
                logging.error(f"failed making a call to {FORWARD_URL} on wf {flow_id}")

        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        next_headers['x-rexflow-original-host'] = o.netloc
        next_headers['x-rexflow-original-path'] = o.path
        requests.post(FAIL_URL, data=data, headers=next_headers)

    def __call__(self):
        while True:  # do forever
            if not self.running:
                break
            try:
                msg = self.get_event()
                if not msg:
                    continue
                data = msg.value()
                headers = dict(msg.headers())
                if FUNCTION == 'CATCH':
                    assert 'x-flow-id' in headers
                    assert 'x-rexflow-wf-id' in headers
                    self.make_call_(
                        data.decode(),
                        flow_id=headers['x-flow-id'].decode(),
                        wf_id=headers['x-rexflow-wf-id'].decode(),
                        content_type=headers['content-type'].decode(),
                    )
                else:
                    self.create_instance(data, headers['content-type'])
            except Exception as e:
                # For some reason, being in a ThreadpoolExecutor suppresses stacktraces, which
                # causes some serious headaches.
                traceback.print_exc()
                logging.error(f"caught exception: {e}")

            time.sleep(2)  # don't get ratelimited by AWS


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.catch_event)

    def health_check(self):
        if kafka is not None:
            # ensure we still have healthy connection to kafka
            kafka.poll(0)
        return "Strong, I am, in the Force!"

    async def catch_event(self):
        response = "For my ally is the Force, and a powerful ally it is."

        data = await request.data
        if FUNCTION == 'START':
            response = self.manager.create_instance(data, request.headers['content-type'])
        else:
            self.manager.make_call_(
                data,
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
                request.headers['content-type'],
            )
        return response

    async def forward_call(self):
        data = await request.data
        requests.post(
            FORWARD_URL,
            headers={
                'x-flow-id': request.headers['x-flow-id'],
                'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
                'content-type': request.headers['content-type'],
            },
            data=data,
        )
        if FUNCTION == "CATCH":
            return "For my ally is the Force, and a powerful ally it is."
        return "TODO"

    def _shutdown(self):
        self.manager.stop()

    def run(self):
        # Only run the kafka poller if there is a properly-configured
        # kafka client
        if kafka is not None:
            self.manager.start()
        super().run()


if __name__ == '__main__':
    app = EventCatchApp(bind='0.0.0.0:5000')
    app.run()
