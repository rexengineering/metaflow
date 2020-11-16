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

import boto3
from botocore.exceptions import ClientError
import json
import os
import re
import requests
import time

from quart import jsonify
from code.executor import get_executor

QUEUE = os.environ['REXFLOW_CATCHGATEWAY_QUEUE']
FORWARD_URL = os.getenv('REXFLOW_CATCHGATEWAY_FORWARD_URL', '')


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
            response = self.kinesis_client.get_records(
                ShardIterator=self.get_iterator(self.stream_info['Shards'][0]),  # assume only 1 shard for now
                Limit=1000,
            )
            for record in response['Records']:
                yield record
            self.shard_it = response['NextShardIterator']
            if self.shard_it is None or response['MillisBehindLatest'] == 0:
                break
            time.sleep(1)

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
                    requests.post(FORWARD_URL, headers={'x-flow-id': str(flow_id), 'x-rexflow-wf-id': str(wf_id)}, json=event)
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
