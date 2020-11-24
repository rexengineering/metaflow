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


KAFKA_HOST = os.environ['KAFKA_HOST']
KAFKA_TOPIC = os.environ['KAFKA_TOPIC']
FORWARD_URL = os.getenv('FORWARD_URL', '')

TOTAL_ATTEMPTS_STR = os.getenv('TOTAL_ATTEMPTS', '')
TOTAL_ATTEMPTS = int(TOTAL_ATTEMPTS_STR) if TOTAL_ATTEMPTS_STR else 2
FAIL_URL = os.getenv('FAIL_URL', 'http://flowd.rexflow:9002/instancefail')

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


class EventThrowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.throw_event)

    def health_check(self):
        kafka.poll(0)
        return "May the Force be with you."

    async def throw_event(self):
        incoming_json = await request.get_json()
        send_to_stream(incoming_json, request.headers['x-flow-id'], request.headers['x-rexflow-wf-id'])
        if FORWARD_URL:
            make_call_(incoming_json)
        return "For my ally is the Force, and a powerful ally it is."


    def run(self):
        super().run()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    app = EventThrowApp(bind='0.0.0.0:5000')
    app.run()
