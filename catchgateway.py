'''
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
'''
import asyncio
import logging
import signal
from typing import Any

from quart import Quart, request
from hypercorn.config import Config
from hypercorn.asyncio import serve
from urllib.parse import urlparse

from confluent_kafka import Consumer
import json
import os
import re
import requests
import time

from quart import jsonify
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
)

KAFKA_HOST = os.environ['KAFKA_HOST']
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
FORWARD_URL = os.getenv('FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.environ['TOTAL_ATTEMPTS'])
FAIL_URL = os.environ['FAIL_URL']

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

    def create_instance(self, incoming_data, headers=None):
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
        )
        if first_task_response is not None:
            if not etcd.replace(keys.state, States.STARTING, BStates.RUNNING):
                logging.error('Failed to transition from STARTING -> ERROR.')
        else:
            if not etcd.replace(keys.state, States.STARTING, States.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')
        return {"id": instance_id}

    def make_call_(self, event, flow_id, wf_id):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
        }
        for _ in range(TOTAL_ATTEMPTS):
            try:
                svc_response = requests.post(FORWARD_URL, headers=next_headers, json=event)
                svc_response.raise_for_status()
                return svc_response
            except Exception:
                logging.error(f"failed making a call to {FORWARD_URL} on wf {flow_id}")

        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        next_headers['x-rexflow-original-host'] = o.netloc
        next_headers['x-rexflow-original-path'] = o.path
        requests.post(FAIL_URL, json=event, headers=next_headers)

    def __call__(self):
        while True:  # do forever
            if not self.running:
                break
            try:
                msg = self.get_event()
                if not msg:
                    continue
                data = msg.value()
                # For now, we insist upon only JSON.
                event_json = json.loads(data.decode())
                headers = dict(msg.headers())
                if FUNCTION == 'CATCH':
                    assert 'x-flow-id' in headers
                    assert 'x-rexflow-wf-id' in headers
                    self.make_call_(event_json, headers['x-flow-id'].decode(), headers['x-rexflow-wf-id'].decode())
                else:
                    self.create_instance(event_json, headers)
            except Exception as e:
                import traceback
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

        incoming_json = await request.get_json()
        if FUNCTION == 'START':
            response = self.manager.create_instance(incoming_json, request.headers)
        else:
            self.manager.make_call_(
                incoming_json,
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
            )
        return response

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
