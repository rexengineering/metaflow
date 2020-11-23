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
from code.executor import get_executor

KAFKA_HOST = os.environ['REXFLOW_CATCHGATEWAY_KAFKA_HOST']
KAFKA_TOPIC = os.environ['REXFLOW_CATCHGATEWAY_KAFKA_TOPIC']
KAFKA_GROUP_ID = os.environ['REXFLOW_CATCHGATEWAY_KAFKA_GROUP_ID']
FORWARD_URL = os.getenv('REXFLOW_CATCHGATEWAY_FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.environ['REXFLOW_CATCHGATEWAY_TOTAL_ATTEMPTS'])
FAIL_URL = os.environ['REXFLOW_CATCHGATEWAY_FAIL_URL']


kafka = Consumer({
    'bootstrap.servers': KAFKA_HOST,
    'group.id': KAFKA_GROUP_ID,
    'auto.offset.reset': 'earliest'
})


class EventCatchPoller:
    def __init__(self, queue_name: str, forward_url: str):
        self.queue_name = queue_name
        self.forward_url = forward_url
        self._seq_num = None
        self.kinesis_client = boto3.client('kinesis', region_name='us-west-2')
        self.stream_info = self.kinesis_client.describe_stream(StreamName=QUEUE)['StreamDescription']
        self.running = False
        self.future = None
        self.executor = get_executor()
        self.shard_it = None

    def start(self):
        assert self.future is None
        self.running = True
        self.future = self.executor.submit(self)

    def stop(self):
        assert self.future is not None
        self.running = False

    def get_iterator(self, shard):
        if self.shard_it:
            return self.shard_it
        shard_id = shard['ShardId']
        resp = self.kinesis_client.get_shard_iterator(
            StreamName=self.queue_name,
            ShardId=shard_id,
            ShardIteratorType='LATEST',
        )
        self.shard_it = resp['ShardIterator']
        return self.shard_it

    def get_events(self):
        # This is a toy demo prototype since we are not going to be using Kinesis in our
        # production system. Therefore, I do not bother with the Kinesis-specific work of
        # coordinating between multiple readers of the same queue.

        while True:  # iterate through all records in stream
            if not self.running:
                break
            kin_response = self.kinesis_client.get_records(
                ShardIterator=self.get_iterator(self.stream_info['Shards'][0]),  # assume only 1 shard for now
                Limit=1000,
            )
            for record in kin_response['Records']:
                print("Got a record: ", record, flush=True)
                yield record
            self.shard_it = kin_response['NextShardIterator']
            if self.shard_it is None or kin_response['MillisBehindLatest'] == 0:
                break
            time.sleep(1)

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
                for record in self.get_events():
                    event = json.loads(record['Data'])
                    self._seq_num = record['SequenceNumber']
                    flow_id = event.pop('x-flow-id')
                    wf_id = event.pop('x-rexflow-wf-id')
                    self.make_call_(event, flow_id, wf_id)
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
        self.manager = EventCatchPoller(QUEUE, FORWARD_URL)
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
        return "For my ally is the Force, and a powerful ally it is."

    def _shutdown(self):
        self.manager.stop()

    def run(self):
        self.manager.start()
        super().run()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    app = EventCatchApp(bind='0.0.0.0:5000')
    app.run()
