'''
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
'''
import logging
import asyncio
import threading
import datetime
from typing import Dict

from quart import request, jsonify, Response
from urllib.parse import urlparse

from confluent_kafka import Consumer
import json
import os
import requests

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
    flow_result,
)

from flowlib.config import get_kafka_config, INSTANCE_FAIL_ENDPOINT

KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', '')
FORWARD_URL = os.getenv('FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.getenv('TOTAL_ATTEMPTS', '2'))
KAFKA_POLLING_PERIOD = 10

FORWARD_TASK_ID = os.environ['FORWARD_TASK_ID']

FUNCTION = os.getenv('REXFLOW_CATCH_START_FUNCTION', 'CATCH')
WF_ID = os.getenv('WF_ID', None)
API_WRAPPER_ENABLED = os.getenv("REXFLOW_API_WRAPPER_ENABLED") != "FALSE"
API_WRAPPER_TIMEOUT = int(os.getenv("REXFLOW_API_WRAPPER_TIMEOUT", "5"))
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)


kafka = None
KAFKA_CONFIG = get_kafka_config()
if KAFKA_CONFIG is not None and KAFKA_TOPIC is not None:
    config = {
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
    config.update(KAFKA_CONFIG)
    kafka = Consumer(config)
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
        msg = kafka.poll(KAFKA_POLLING_PERIOD)
        return msg

    def run_instance(self, keys, incoming_data, instance_id, content_type, etcd):
        etcd.put(keys.parent, WF_ID)
        first_task_response = self.make_call_(
            incoming_data,
            instance_id,
            WF_ID,
            content_type,
        )
        if first_task_response is not None:
            if not etcd.replace(keys.state, States.STARTING, BStates.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')
        else:
            if not etcd.replace(keys.state, States.STARTING, States.ERROR):
                logging.error('Failed to transition from STARTING -> ERROR.')

    def create_instance(self, incoming_data, content_type) -> Dict[str, object]:
        instance_id = workflow.WorkflowInstance.new_instance_id(str(WF_ID))
        etcd = get_etcd()
        keys = WorkflowInstanceKeys(instance_id)
        if not etcd.put_if_not_exists(keys.state, BStates.STARTING):
            # Should never happen...unless there's a collision in uuid1
            logging.error(f'{keys.state} already defined in etcd!')
            return flow_result(-1, f"Internal Error: ID {instance_id} already "
                "exists", id=None)

        self.executor.submit(
            self.run_instance, keys, incoming_data, instance_id, content_type, etcd
        )
        return flow_result(0, 'Ok', id=instance_id)

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

    def _shadow_to_kafka(self, data, headers):
        if not KAFKA_SHADOW_URL:
            return
        o = urlparse(FORWARD_URL)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        try:
            requests.post(KAFKA_SHADOW_URL, headers=headers, data=data).raise_for_status()
        except Exception:
            logging.warning("Failed shadowing traffic to Kafka")

    def make_call_(self, data, flow_id, wf_id, content_type):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
            'content-type': content_type,
            'x-rexflow-task-id': FORWARD_TASK_ID,
        }
        for _ in range(TOTAL_ATTEMPTS):
            try:
                svc_response = requests.post(FORWARD_URL, headers=next_headers, data=data)
                svc_response.raise_for_status()
                try:
                    self.save_traceid(svc_response.headers, flow_id)
                except Exception as exn:
                    logging.exception("Failed to save trace id on WF Instance", exc_info=exn)
                self._shadow_to_kafka(data, next_headers)
                return svc_response
            except Exception as exn:
                logging.exception(
                    f"failed making a call to {FORWARD_URL} on wf {flow_id}",
                    exc_info=exn,
                )

        # Notify Flowd that we failed.
        o = urlparse(FORWARD_URL)
        next_headers['x-rexflow-original-host'] = o.netloc
        next_headers['x-rexflow-original-path'] = o.path
        requests.post(INSTANCE_FAIL_ENDPOINT, data=data, headers=next_headers)
        next_headers['x-rexflow-failure'] = True
        self._shadow_to_kafka(data, next_headers)

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
                    assert headers['x-rexflow-wf-id'].decode() == WF_ID
                    self.make_call_(
                        data.decode(),
                        flow_id=headers['x-flow-id'].decode(),
                        wf_id=headers['x-rexflow-wf-id'].decode(),
                        content_type=headers['content-type'].decode(),
                    )
                else:
                    self.create_instance(data, headers['content-type'])
            except Exception as exn:
                logging.exception("Failed processing event", exc_info=exn)


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.catch_event)
        self.executor = get_executor()
        if FUNCTION == 'START' and API_WRAPPER_ENABLED:
            self.app.route('/wrapper', methods=['POST'])(self.synchronous_wrapper)

    def health_check(self):
        return jsonify(flow_result(0, ""))

    async def catch_event(self):
        response = jsonify(flow_result(0, ""))

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

    async def get_result(self, instance_id, watch_iter, cancel_watch):
        key_results = {
            "state": None,
            "result": None,
            "content_type": None,
        }
        for event in watch_iter:
            full_key = event.key.decode('utf-8')
            key = full_key.split('/')[-1]
            if key in key_results:
                value = event.value.decode('utf-8')
                key_results[key] = value
                if all([key_results[k] is not None for k in key_results.keys()]):
                    cancel_watch()
                    return key_results
        return None

    async def synchronous_wrapper(self):
        start = datetime.datetime.now()
        etcd = get_etcd()
        data = await request.data
        instance_id = self.manager.create_instance(data, request.headers['content-type'])['id']
        watch_iter, cancel_watch = etcd.watch_prefix(WorkflowInstanceKeys.key_of(instance_id))
        wait_task = asyncio.create_task(self.get_result(instance_id, watch_iter, cancel_watch))
        timer = threading.Timer(API_WRAPPER_TIMEOUT, self._cleanup_watch_iter, [cancel_watch])
        timer.start()
        result = await wait_task
        if not result:
            response = Response("WF Instance Timed Out.", 500)
        else:
            response = Response(result['result'])
            response.headers['content-type'] = result['content_type']
        response.headers['x-flow-id'] = instance_id

        end = datetime.datetime.now()
        print("start: ", start, "end:", end)
        print(end - start, flush=True)
        return response

    def _cleanup_watch_iter(self, cancel_watch):
        try:
            cancel_watch()
        except Exception as e:
            logging.exception("failed...", exc_info=e)

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
