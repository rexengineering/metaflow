"""
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
"""
import logging

import asyncio
import threading
import datetime
from typing import Dict, NoReturn
from isodate import ISO8601Error
from quart import request, jsonify, Response
from quart_cors import cors

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
assert WF_ID is not None, 'Config error - WF_ID not in env!'
TID = os.getenv('TID', None)
assert TID is not None, 'Config error - TID not in env!'

API_WRAPPER_ENABLED = os.getenv("REXFLOW_API_WRAPPER_ENABLED") != "FALSE"
API_WRAPPER_TIMEOUT = int(os.getenv("REXFLOW_API_WRAPPER_TIMEOUT", "10"))
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)

"""
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

"""
TIMED_EVENT_DESCRIPTION = os.getenv(TIMER_DESCRIPTION, None)
IS_TIMED_EVENT          = TIMED_EVENT_DESCRIPTION is not None
IS_TIMED_START_EVENT    = IS_TIMED_EVENT and FUNCTION == FUNCTION_START
IS_TIMED_CATCH_EVENT    = IS_TIMED_EVENT and FUNCTION == FUNCTION_CATCH

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
        if IS_TIMED_EVENT:
            callback, name = (self.create_instance, 'start') if IS_TIMED_START_EVENT else (self.make_call_impl, 'catch')
            logging.info(f'Timed {name} event {TIMED_EVENT_DESCRIPTION}')
            self.timed_manager = TimedEventManager(TIMED_EVENT_DESCRIPTION, callback, IS_TIMED_START_EVENT)

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
    
    def create_timed_instance(self, incoming_data:str, content_type:str) -> NoReturn:
        # create_timer(self, wf_inst_id, token_stack, args)
        # --> proxies call to create_instance(incoming_data, content_type, instance_id)
        self.timed_manager.create_timer(None, None, [incoming_data, content_type, None])

    def run_instance(self, keys, incoming_data, instance_id, content_type, etcd):
        logging.info(f'Running instance {instance_id}')
        etcd.put(keys.parent, WF_ID)
        first_task_response = self._make_call(
            incoming_data,
            instance_id,
            WF_ID,
            content_type,
        )
        # it is possible for the the workflow instance to COMPLETE before we even
        # get here. If so, let it be.
        cur_state,_ = etcd.get(keys.state)
        if cur_state == BStates.COMPLETED:
            logging.info(f'{keys.state} already completed')
        else:
            if first_task_response is not None:
                if not etcd.replace(keys.state, States.STARTING, BStates.RUNNING):
                    logging.error(f'Failed to transition {keys.state} from STARTING -> RUNNING.')
            else:
                if not etcd.replace(keys.state, States.STARTING, States.ERROR):
                    logging.error(f'Failed to transition {keys.state} from STARTING -> ERROR.')

    def create_instance(self, incoming_data, content_type, instance_id=None) -> Dict[str, object]:
        # Allow instance_id to be passed into this function in case a caller needs
        # to have a watch_iter on the instance keys _before_ the instance gets created.
        # This prevents the watch_iter from just dangling if, for example, the instance
        # goes to the error state before this function returns.
        instance_id = instance_id or workflow.WorkflowInstance.new_instance_id(str(WF_ID))
        logging.info(f'Creating instance {instance_id}')
        etcd = get_etcd()
        keys = WorkflowInstanceKeys(instance_id)
        if not etcd.put_if_not_exists(keys.state, BStates.STARTING):
            # Should never happen...unless there's a collision in uuid1
            logging.error(f'{keys.state} already defined in etcd!')
            return flow_result(-1, f"Internal Error: ID {instance_id} already exists", id=None)

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
        # TODO: REXFLOW-188 Move kafka shadowing to a utility, make everything use that utility,
        # and get rid of these hardcoded headers.
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        try:
            requests.post(KAFKA_SHADOW_URL, headers=headers, data=data).raise_for_status()
        except Exception:
            logging.warning("Failed shadowing traffic to Kafka")

    def _make_call(self, data:str, flow_id:str, wf_id:str, content_type:str, token_stack:str = None):
        # Note: Python is garbage; so don't set `{}` as a default argument to a function. Because a dict is
        # an object, it only gets instantiated once, which means repeated calls to the same function could
        # have WEIRD side effects.
        if IS_TIMED_CATCH_EVENT:
            self.timed_manager.create_timer(flow_id, token_stack, [data, flow_id, wf_id, content_type])
            return jsonify(flow_result(0, ""))

        return self.make_call_impl(token_stack, data, flow_id, wf_id, content_type)

    def make_call_impl(self, token_stack:str, data:str, flow_id:str, wf_id:str, content_type:str):
        next_headers = {
            Headers.X_HEADER_FLOW_ID: str(flow_id),
            Headers.X_HEADER_WORKFLOW_ID: str(wf_id),
            Headers.CONTENT_TYPE: content_type,
            Headers.X_HEADER_TASK_ID: FORWARD_TASK_ID,
        }
        if token_stack:
            next_headers[Headers.X_HEADER_TOKEN_POOL_ID.lower()] = token_stack

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

        # Same TODO: See REXFLOW-188
        next_headers[Headers.X_REXFLOW_ORIGINAL_HOST] = o.netloc
        next_headers[Headers.X_REXFLOW_ORIGINAL_PATH] = o.path
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
            next_headers[Headers.X_REXFLOW_FAILURE] = True
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
                    assert Headers.X_HEADER_FLOW_ID in headers
                    assert Headers.X_HEADER_WORKFLOW_ID in headers
                    assert headers[Headers.X_HEADER_WORKFLOW_ID].decode() == WF_ID
                    token_header = headers.get(Headers.X_HEADER_TOKEN_POOL_ID.lower())
                    if token_header:
                        token_header = token_header.decode()

                    self._make_call(
                        data.decode(),
                        flow_id=headers[Headers.X_HEADER_FLOW_ID].decode(),
                        wf_id=headers[Headers.X_HEADER_WORKFLOW_ID].decode(),
                        content_type=headers[Headers.CONTENT_TYPE.lower()].decode(),
                        token_stack=token_header
                    )
                else:
                    self.create_instance(data, headers[Headers.CONTENT_TYPE.lower()])
            except Exception as exn:
                logging.exception("Failed processing event", exc_info=exn)


class EventCatchApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = EventCatchPoller(FORWARD_URL)
        self.executor = get_executor()
        self.app = cors(self.app)

        self.app.route('/', methods=['GET'])(self.health_check)
        if FUNCTION == FUNCTION_CATCH or not IS_TIMED_EVENT:
            self.app.route('/', methods=['POST'])(self.catch_event)
            if FUNCTION == FUNCTION_START and API_WRAPPER_ENABLED:
                self.app.route('/wrapper', methods=['POST'])(self.synchronous_wrapper)
        if IS_TIMED_EVENT:
            self.app.route('/timer', methods=['GET','POST'])(self.timer_query)
        if IS_TIMED_START_EVENT:
            # start running timed start events immediately
            logging.info('Starting timed instance')
            self.manager.create_timed_instance('[]','application/json')

    def health_check(self):
        if FUNCTION == FUNCTION_START:
            # TODO: clean up all the calls to get_etcd().
            # We just want to make sure we can indeed connect. This should be just
            # a call to `self._etcd.get('foo')`, but we don't have a self._etcd yet.
            etcd = get_etcd()

            # Still need to call .get(foo) because we could have lost connection to
            # the etcd server between now and when the _etcd global was initialized.
            etcd.get('healthcheck')
        return jsonify(flow_result(0, ""))

    async def catch_event(self):
        response = jsonify(flow_result(0, ""))

        data = await request.data
        if FUNCTION == FUNCTION_START:
            response = self.manager.create_instance(data, request.headers['content-type'])
        else: #if FUNCTION == FUNCTION_CATCH
            self.manager._make_call(
                data,
                request.headers[Headers.X_HEADER_FLOW_ID.lower()],
                request.headers[Headers.X_HEADER_WORKFLOW_ID.lower()],
                request.headers[Headers.CONTENT_TYPE.lower()],
                request.headers.get(Headers.X_HEADER_TOKEN_POOL_ID)
            )
        return response

    async def timer_query(self):
        """
        Provide an API to query and modify timer description
        GET returns the timer specification
        POST sets the timer specification and takes a JSON packet:

        { 'timer_type' : <timer_type>, 'timer_spec' : <timer_spec>}

        The type and spec are identical to those specified in the
        BPMN.
        """
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
                if IS_TIMED_START_EVENT:
                    logging.info('start timed instances')
                    self.manager.create_timed_instance('[]','applicaton/json')
                response = flow_result(0, 'Ok')
            except (ISO8601Error,Exception) as ex:
                response = flow_result(-1, str(ex))

        return jsonify(response)

    async def get_result(self, instance_id, watch_iter, cancel_watch):
        keys_obj = WorkflowInstanceKeys(instance_id)
        relevant_keys = [
            keys_obj.state,
            keys_obj.result,
            keys_obj.content_type,
        ]
        result = {}
        for event in watch_iter:
            key = event.key.decode('utf-8')
            if key in relevant_keys:
                value = event.value.decode('utf-8')
                if key == keys_obj.state:
                    if value in [States.ERROR, States.COMPLETED, States.STOPPED]:
                        result['state'] = value
                elif key == keys_obj.result:
                    result['result'] = value
                elif key == keys_obj.content_type:
                    result['content-type'] = value
                if len(list(result.keys())) == len(relevant_keys):
                    cancel_watch()
        return result

    async def synchronous_wrapper(self):
        etcd = get_etcd()
        data = await request.data
        instance_id = workflow.WorkflowInstance.new_instance_id(str(WF_ID))
        watch_iter, cancel_watch = etcd.watch_prefix(WorkflowInstanceKeys.key_of(instance_id))
        self.manager.create_instance(data, request.headers['content-type'], instance_id=instance_id)
        wait_task = asyncio.create_task(self.get_result(instance_id, watch_iter, cancel_watch))
        timer = threading.Timer(API_WRAPPER_TIMEOUT, self._cleanup_watch_iter, [cancel_watch])
        timer.start()
        instance_result = await wait_task # type: dict

        response_status = None
        response_payload = None
        content_type = instance_result.get('content-type', 'application/octet-stream')

        # If everything went well, we'll have three keys: state, content-type, and result
        # If we don't have that, then the instance timed out.
        if instance_result.get('state') == States.COMPLETED:
            # Just return the direct result unmodified with an 'OK' status.
            response_status = 200
            response_payload = instance_result['result']
        elif instance_result.get('state') is None:
            # The instance didn't terminate before we got here, so we return
            # a timeout.
            response_status = 504
            response_payload = json.dumps(flow_result(
                -1,
                "WF Instance Timed Out",
            ))
            content_type = 'application/json'
        elif instance_result.get('state') in [States.ERROR, States.STOPPED]:
            # Note: As of this commit, the only difference in usage between
            # the STOPPED and ERROR state is that the STOPPED state allows for a
            # retry (i.e. WorkflowProperties.is_recoverable == True). A decision
            # was made that it should be impossible to do a retry on an instance
            # in the ERROR state (since the transition from ERROR -> RUNNING was
            # deemed not good). Therefore, if we want to be able to retry, we
            # put the instance in the STOPPED state.
            response_status = 500

            # If the error-handling in the `http://flowd/instancefail` endpoint
            # went as planned, we should have a JSON blob containing a bunch of
            # error information. If we do, then we load it and splat it. Otherwise,
            # we just return the bytes.
            error_data = {}
            if 'result' in instance_result:
                result = instance_result['result']
                if content_type == 'application/json':
                    error_data = json.loads(instance_result['result'])
                else:
                    error_data = {
                        'error_data': instance_result['result'],
                        'error_data_type': content_type,
                    }
            response_payload = json.dumps(flow_result(
                -1,
                "WF Instance Failed.",
                **error_data,
            ))

            # We're explicitly returning a json here, since we formed one just above.
            content_type = 'application/json'
        else:
            assert False, "self.get_result() shouldn't return a thing like this."

        response = Response(
            response_payload.encode(),
            status=response_status,
            content_type=content_type,
        )
        response.headers[Headers.X_HEADER_FLOW_ID] = instance_id
        response.headers['access-control-allow-origin'] = '*'
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
