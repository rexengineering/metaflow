'''
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
'''
import logging

import asyncio
import threading
import datetime
from typing import Dict, NoReturn
from isodate import ISO8601Error
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
    Headers,
    X_HEADER_TOKEN_POOL_ID,
    flow_result,
    TIMER_DESCRIPTION,
)
from flowlib.timer_util import (
    TimedEventManager,
)

from flowlib.config import get_kafka_config, INSTANCE_FAIL_ENDPOINT, CATCH_LISTEN_PORT

FUNCTION_CATCH = 'CATCH'
FUNCTION_START = 'START'
FUNCTION = os.getenv('REXFLOW_CATCH_START_FUNCTION', FUNCTION_CATCH)

KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', None)
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', '')
FORWARD_URL = os.getenv('FORWARD_URL', '')
TOTAL_ATTEMPTS = int(os.getenv('TOTAL_ATTEMPTS', '2'))
KAFKA_POLLING_PERIOD = 10

FORWARD_TASK_ID = os.environ['FORWARD_TASK_ID']

WF_ID = os.getenv('WF_ID', None)
API_WRAPPER_ENABLED = os.getenv("REXFLOW_API_WRAPPER_ENABLED") != "FALSE"
API_WRAPPER_TIMEOUT = int(os.getenv("REXFLOW_API_WRAPPER_TIMEOUT", "5"))
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)

'''
The TIMER_DESCRIPTION will contain pertainent data for the timer defined
by the BPMN. This consists of a JSON string formatted as follows:
["time_type","timer_spec"]

Where timer_type is timeDate, timeCycle, or timeDuration
      timer_spec is a ISO 8601-1 specification for the timer apropos for
                 the timer_type
                 timeDate - DateTime (4.3) in GMT/UTC (Zulu)
                 timeDuration - Duration (4.4.2.b)
                 timeCycle - Recurrence (4.5.2)
                    Infinite recurrences are not permitted, hence
                    R/<duration> or R0/<duration> are invalid.

'''
TIMED_EVENT_DESCRIPTION = os.getenv(TIMER_DESCRIPTION, '')
TIMED_START_EVENT = TIMED_EVENT_DESCRIPTION and FUNCTION == FUNCTION_START

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
        self.timed_manager = None
        if TIMED_EVENT_DESCRIPTION:
            if FUNCTION == FUNCTION_CATCH:
                logging.info(f'Timed event {TIMED_EVENT_DESCRIPTION}')
                self.timed_manager = TimedEventManager(TIMED_EVENT_DESCRIPTION, self.make_call_impl, use_tokens = True)
            else: #if FUNCTION == FUNCTION_START:
                logging.info(f'Timed start event {TIMED_EVENT_DESCRIPTION}')
                self.timed_manager = TimedEventManager(TIMED_EVENT_DESCRIPTION, self.create_instance, use_tokens = False)

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
        logging.info(f'Running instance {instance_id}')
        etcd.put(keys.parent, WF_ID)
        first_task_response = self._make_call(
            incoming_data,
            instance_id,
            WF_ID,
            content_type,
        )
        if first_task_response is not None:
            if not etcd.replace(keys.state, States.STARTING, BStates.RUNNING):
                logging.error('Failed to transition {keys.state} from STARTING -> RUNNING.')
        else:
            if not etcd.replace(keys.state, States.STARTING, States.ERROR):
                logging.error('Failed to transition {keys.state} from STARTING -> ERROR.')

    def create_timed_instance(self, incoming_data, content_type) -> NoReturn:
        self.timed_manager.create_timer(WF_ID, None, [incoming_data, content_type])

    def create_instance(self, incoming_data, content_type) -> Dict[str, object]:
        instance_id = workflow.WorkflowInstance.new_instance_id(str(WF_ID))
        logging.info(f'Creating instance {instance_id}')
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
        if Headers.TRACEID_HEADER in headers:
            trace_id = headers[Headers.TRACEID_HEADER]
        elif Headers.TRACEID_HEADER.lower() in headers:
            trace_id = headers[Headers.TRACEID_HEADER.lower()]

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

    def _make_call(self, data : str, flow_id : str, wf_id : str, content_type : str, token_stack : str = None):
        # Note: Python is crap; so don't set `{}` as a default argument to a function. Because a dict is
        # an object, it only gets instantiated once, which means repeated calls to the same function could
        # have WEIRD side effects.
        if self.timed_manager and FUNCTION == FUNCTION_CATCH:
            self.timed_manager.create_timer(flow_id, token_stack, [data, flow_id, wf_id, content_type])
            return True
        else:
            return self.make_call_impl(token_stack, data, flow_id, wf_id, content_type)

    def make_call_impl(self, token_stack : str, data : str, flow_id : str, wf_id : str, content_type : str):
        next_headers = {
            'x-flow-id': str(flow_id),
            'x-rexflow-wf-id': str(wf_id),
            'content-type': content_type,
            'x-rexflow-task-id': FORWARD_TASK_ID,
        }
        if token_stack:
            next_headers[X_HEADER_TOKEN_POOL_ID.lower()] = token_stack

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
        try:
            response = requests.post(INSTANCE_FAIL_ENDPOINT, data=data, headers=next_headers)
            logging.info(response)
            response.raise_for_status()
        except Exception as exn:
            logging.exception(
                f"Instance: {flow_id}. Failed to notify flowd of error.",
                exc_info=exn,
            )
            return None
        finally:    
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
                if FUNCTION == FUNCTION_CATCH:
                    assert 'x-flow-id' in headers
                    assert 'x-rexflow-wf-id' in headers
                    assert headers['x-rexflow-wf-id'].decode() == WF_ID
                    token_header = headers.get(X_HEADER_TOKEN_POOL_ID.lower())
                    if token_header:
                        token_header = token_header.decode()

                    self._make_call(
                        data.decode(),
                        flow_id=headers['x-flow-id'].decode(),
                        wf_id=headers['x-rexflow-wf-id'].decode(),
                        content_type=headers['content-type'].decode(),
                        token_stack=token_header
                    )
                else:
                    self.create_instance(data, headers['content-type'])
            except Exception as exn:
                logging.exception("Failed processing event", exc_info=exn)


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.executor = get_executor()
        self.app.route('/', methods=['GET'])(self.health_check)
        if FUNCTION == FUNCTION_CATCH or (self.manager.timed_manager is None):
            self.app.route('/', methods=['POST'])(self.catch_event)
            if FUNCTION == FUNCTION_START and API_WRAPPER_ENABLED:
                    self.app.route('/wrapper', methods=['POST'])(self.synchronous_wrapper)
        if TIMED_START_EVENT:
            # start running timed start events immediately, instead of
            # waiting for a flowctl run.
            logging.info("Starting timed instance")
            self.manager.create_timed_instance('[]','application/json')
            self.app.route('/timer', methods=['GET','POST'])(self.timer_query)

    def health_check(self):
        return jsonify(flow_result(0, ""))

    async def catch_event(self):
        response = jsonify(flow_result(0, ""))

        data = await request.data
        if FUNCTION == FUNCTION_START:
            response = self.manager.create_instance(data, request.headers['content-type'])
        else: #if FUNCTION == FUNCTION_CATCH
            self.manager._make_call(
                data,
                request.headers['x-flow-id'],
                request.headers['x-rexflow-wf-id'],
                request.headers['content-type'],
                request.headers.get(X_HEADER_TOKEN_POOL_ID)
            )
        return response

    async def timer_query(self):
        '''
        Provide an API to query and modify timer description
        GET returns the timer specification
        POST sets the timer specification and takes a JSON packet:

        { 'timer_type' : <timer_type>, 'timer_spec' : <timer_spec>}

        The type and spec are identical to those specified in the
        BPMN.
        '''
        data = await request.data
        if request.method == 'GET':
            # return information about the existing timers
            aspects = self.manager.timed_manager.aspects
            response = flow_result(0, 'Ok', timer_type=aspects.timer_type_s, timer_spec=aspects.spec, timer_done=self.manager.timed_manager.completed)
        else: #if request.method == 'POST'
            # update the existing timer
            req = json.loads(data)
            try:
                # the following raises if the anything is invalid
                results = TimedEventManager.validate_spec(req['timer_type'],req['timer_spec'].upper() )
                # the following raises if the current timer is not finished
                self.manager.timed_manager.reset(results)
                logging.info(f'Timer reset to {req["timer_type"]}, {req["timer_spec"]}')
                if TIMED_START_EVENT:
                    # start running timed start events immediately, instead of
                    # waiting for a flowctl run.
                    logging.info('Starting timed instance')
                    self.manager.create_timed_instance('[]','application/json')
                response = flow_result(0, 'Ok')
            except (ISO8601Error,Exception) as ex:
                response = flow_result(-1, str(ex))

        return jsonify(response)

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

        # now bring up the web server (this call blocks)
        super().run()


if __name__ == '__main__':
    app = EventCatchApp(bind=f'0.0.0.0:{CATCH_LISTEN_PORT}')
    app.run()
