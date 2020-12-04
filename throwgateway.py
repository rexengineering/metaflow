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


KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', '')
FORWARD_URL = os.getenv('FORWARD_URL', '')

TOTAL_ATTEMPTS_STR = os.getenv('TOTAL_ATTEMPTS', '')
TOTAL_ATTEMPTS = int(TOTAL_ATTEMPTS_STR) if TOTAL_ATTEMPTS_STR else 2
FAIL_URL = os.getenv('FAIL_URL', 'http://flowd.rexflow:9002/instancefail')

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
    }
    if 'x-b3-trace-id' in request.headers:
        headers['x-b3-trace-id'] = request.headers['x-b3-trace-id']

    success = False
    for _ in range(TOTAL_ATTEMPTS):
        try:
            next_response = requests.post(FORWARD_URL, headers=headers, data=data)
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
        requests.post(FAIL_URL, data=data, headers=headers)


class EventThrowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.throw_event)

    def health_check(self):
        kafka.poll(0)
        return "May the Force be with you."

    async def throw_event(self):
        data = await request.data
        send_to_stream(
            data,
            request.headers['x-flow-id'],
            request.headers['x-rexflow-wf-id'],
            request.headers['content-type'],
        )
        if FORWARD_URL:
            make_call_(data)
        return "For my ally is the Force, and a powerful ally it is."


    def run(self):
        super().run()


if __name__ == '__main__':
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
