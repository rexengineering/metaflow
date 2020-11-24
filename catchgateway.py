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

KAFKA_HOST = os.environ['KAFKA_HOST']
KAFKA_TOPIC = os.environ['KAFKA_TOPIC']
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

    def make_call_(self, event, flow_id, wf_id):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
        }
        success = False
        for _ in range(TOTAL_ATTEMPTS):
            try:
                svc_response = requests.post(FORWARD_URL, headers=next_headers, json=event)
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
                assert 'x-flow-id' in headers
                assert 'x-rexflow-wf-id' in headers
                self.make_call_(event_json, headers['x-flow-id'].decode(), headers['x-rexflow-wf-id'].decode())
            except Exception as e:
                import traceback
                # For some reason, being in a ThreadpoolExecutor suppresses stacktraces, which
                # causes some serious headaches.
                traceback.print_exc()
                raise e
            time.sleep(2)  # don't get ratelimited by AWS


class QuartApp:
    # Plagiarized from Jon's `flowlib` code.
    def __init__(self, name, **kws):
        self.app = Quart(name)
        self.config = Config.from_mapping(kws)
        self.shutdown_event = asyncio.Event()

    def _shutdown(self):
        pass

    def _termination_handler(self, *_: Any, exn:Exception = None) -> None:
        if exn:
            logging.exception(exn)
            logging.info(f'Shutting down {self.app.name} daemon...')
        else:
            logging.info(f'SIGTERM received, shutting down {self.app.name} '
                          'daemon...')
        self._shutdown()
        self.shutdown_event.set()

    def run(self):
        logging.debug('QuartApp.run() called...')
        try:
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGTERM, self._termination_handler)
            return loop.run_until_complete(serve(
                self.app, self.config, shutdown_trigger=self.shutdown_event.wait
            ))
        except (KeyboardInterrupt, Exception) as exn:
            self._termination_handler(exn=exn)


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.forward_call)

    def health_check(self):
        return "May the Force be with you."

    async def forward_call(self):
        incoming_json = await request.get_json()
        requests.post(
            FORWARD_URL,
            headers={'x-flow-id': request.headers['x-flow-id'], 'x-rexflow-wf-id': request.headers['x-rexflow-wf-id']},
            json=incoming_json,
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
