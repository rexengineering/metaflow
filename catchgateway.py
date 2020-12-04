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

KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', '')
KAFKA_GROUP_ID = os.environ['KAFKA_GROUP_ID']
FORWARD_URL = os.getenv('FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.environ['TOTAL_ATTEMPTS'])
FAIL_URL = os.environ['FAIL_URL']

FUNCTION = os.getenv('REXFLOW_CATCH_START_FUNCTION', 'CATCH')
WF_ID = os.getenv('REXFLOW_WF_ID', None)


kafka = None
if KAFKA_TOPIC:    
    kafka = Consumer({
        'bootstrap.servers': KAFKA_HOST,
        'group.id': KAFKA_GROUP_ID,
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

    def make_call_(self, data, flow_id, wf_id, content_type):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
            'content-type': content_type,
        }
        success = False
        for _ in range(TOTAL_ATTEMPTS):
            try:
                svc_response = requests.post(FORWARD_URL, headers=next_headers, data=data)
                svc_response.raise_for_status()
                success = True
                break
            except Exception:
                print(f"failed making a call to {FORWARD_URL} on wf {flow_id}", flush=True)

        if not success:
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
                assert 'x-flow-id' in headers
                assert 'x-rexflow-wf-id' in headers
                self.make_call_(
                    data.decode(),
                    flow_id=headers['x-flow-id'].decode(),
                    wf_id=headers['x-rexflow-wf-id'].decode(),
                    content_type=headers['content-type'].decode(),
                )
            except Exception as e:
                import traceback
                # For some reason, being in a ThreadpoolExecutor suppresses stacktraces, which
                # causes some serious headaches.
                traceback.print_exc()
                raise e
            time.sleep(2)  # don't get ratelimited by AWS


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.forward_call)

    def health_check(self):
        return "May the Force be with you."

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
        if kafka is not None:
            self.manager.start()
        super().run()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    app = EventCatchApp(bind='0.0.0.0:5000')
    app.run()
