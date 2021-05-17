import asyncio
from collections import defaultdict
import base64
import logging
import json

from async_timeout import timeout
from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp
from flowlib.workflow import Workflow, get_workflows

from flowlib.config import (
    INSTANCE_FAIL_ENDPOINT_PATH,
    WF_MAP_ENDPOINT_PATH
)
from flowlib.constants import (
    BStates,
    flow_result,
    WorkflowInstanceKeys,
    Headers,
)
from flowlib import token_api


TIMEOUT_SECONDS = 10


def convert_envoy_hdr_msg_to_dict(headers_bytes):
    headers_str = base64.b64decode(headers_bytes).decode()
    hdrs = {}
    for header in headers_str.split('\n'):
        # note: Envoy puts a `:` at the start of the path, authority, and host headers for
        # some reason.
        header = header.lstrip(':')
        hdr_key = header[:header.find(':')]
        hdr_val = header[header.find(':') + 1:]
        if len(hdr_key) > 0:
            hdrs[hdr_key] = hdr_val
    return hdrs


def process_data(encoded_str, data_should_be_json):
    '''Accepts a string of b64-encoded data. Tries the following steps, saving
    the result each time. If any of the steps fails, it returns the most recent
    success. If no processing step succeeds (i.e. the result of decoding the
    data not an ascii-representable string), then we just return the original
    input: the base64-encoded string. Steps:
    1. Try to decode the base64-encoded string into something ascii-readable.
    2. If data_should_be_json, then we try to load the json into a python dict.
    '''
    result = encoded_str
    # Step 1: Try to make it a human-readable string
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        if decoded_bytes.isascii():
            decoded_str = decoded_bytes.decode()
            result = decoded_str
            if data_should_be_json:
                result = json.loads(result)
        elif data_should_be_json:
            logging.warning(
                f"Should've been able to json load this but it wasn't even ascii: {encoded_str}"
            )
    except json.decoder.JSONDecodeError as exn:
        logging.exception(
            f"Should've been able to json load the data but couldn't: {encoded_str}",
            exc_info=exn,
        )
    except Exception as exn:
        logging.exception(
            f"Caught an unexpected exception processing `{encoded_str}`:",
            exc_info=exn,
        )
    return result


class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/health', methods=['GET'])(self.health)
        self.app.route('/', methods=['POST'])(self.root_route)
        self.app.route(INSTANCE_FAIL_ENDPOINT_PATH, methods=(['POST']))(self.fail_route)
        self.app.route(WF_MAP_ENDPOINT_PATH, methods=['GET', 'POST'])(self.wf_map)

    async def health(self):
        self.etcd.get('Is The Force With Us?')
        return flow_result(0, "Ok.")

    async def root_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to completed.
        if Headers.X_HEADER_FLOW_ID in request.headers:
            flow_id = request.headers[Headers.X_HEADER_FLOW_ID]
            keys = WorkflowInstanceKeys(flow_id)
            good_states = {BStates.STARTING, BStates.RUNNING}
            if self.etcd.get(keys.state)[0] in good_states:
                if transition_state(self.etcd, keys.state, good_states, BStates.COMPLETED):
                    self.etcd.put(keys.result, await request.data)
                else:
                    logging.error(
                        f'Race on {keys.state}; state changed out of known'
                        ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'

    async def fail_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to ERROR.

        if Headers.X_HEADER_WORKFLOW_ID not in request.headers or Headers.X_HEADER_FLOW_ID not in request.headers:
            return

        flow_id = request.headers[Headers.X_HEADER_FLOW_ID]
        wf_id = request.headers[Headers.X_HEADER_WORKFLOW_ID]
        timer_pool_id = request.headers.get(Headers.X_HEADER_TOKEN_POOL_ID)
        workflow = Workflow.from_id(wf_id)
        keys = WorkflowInstanceKeys(flow_id)
        state_key = keys.state
        good_states = {BStates.STARTING, BStates.RUNNING}

        if self.etcd.get(state_key)[0] in good_states:
            # As per spec, if we have a recoverable workflow we go to STOPPING --> STOPPED.
            # Otherwise, we go straight to ERROR.
            if workflow.process.properties.is_recoverable:
                if not transition_state(self.etcd, state_key, good_states, BStates.STOPPING):
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                        ' good state before state transition could occur!'
                    )
            else:
                if not transition_state(self.etcd, state_key, good_states, BStates.ERROR):
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                        ' good state before state transition could occur!'
                    )

            if timer_pool_id is not None:
                token_api.token_fail(timer_pool_id)

            incoming_data = None
            try:
                with timeout(TIMEOUT_SECONDS):
                    incoming_data = await request.data
            except asyncio.exceptions.TimeoutError as exn:
                logging.exception(
                    f"Timed out waiting for error data on flow id {flow_id}.",
                    exc_info=exn
                )
                self.etcd.put(state_key, BStates.ERROR)
                return

            payload = json.loads(incoming_data.decode())
            self._put_payload(payload, keys, workflow)
            if workflow.process.properties.is_recoverable:
                self.etcd.replace(state_key, BStates.STOPPING, BStates.STOPPED)
        return 'Another happy landing (:'

    def wf_map(self):
        '''Get a map from workflow ID's to workflow deployment ID's.

        Note that this mapping does not assume the workflow ID is "baked" into
        the workflow deployment ID, which it presently is.
        '''
        etcd = get_etcd(is_not_none=True)
        wf_map = {}
        for workflow in get_workflows():
            if etcd.get(workflow.keys.state)[0] == BStates.RUNNING:
                wf_id = workflow.process.xmldict['@id']
                wf_did = workflow.id
                start_event_urls = [
                    start_event.k8s_url
                    for start_event in workflow.process.start_events
                ]
                wf_map[wf_id] = {
                    wf_did: start_event_urls
                }
        return flow_result(0, 'Ok', wf_map=wf_map)

    def _put_payload(self, payload, keys, workflow):
        '''Take all of the incoming data and make it as close to JSON as we possibly
        can. The error data from BAVS looks like:
        {
            'input_headers_encoded': base64-encoded dump of headers of request to the task
            'input_data_encoded': base64-encoded dump of request data to the task
            'output_headers_encoded': (optional) base64-encoded dump of task response headers
            'output_data_encoded': (optional) base64-encoded dump of task response data
            'error_msg': human-readable error message
            'error_code': enum of {
                'CONNECTION_ERROR', 'TASK_ERROR', 'CONTEXT_INPUT_ERROR', 'CONTEXT_OUTPUT_ERROR'
            }
        }
        For the input/output headers/data, we first try to decode them if they're not
        binary data (since BAVS just encodes to avoid having to deal with escaping, etc.).
        If we can successfully decode into a string, we then check if content-type is json,
        and if so, we make it a dict.

        Finally, after processing, we dump the whole dict into the `result` key, and
        since we're putting a `json.dumps()` into the `result` key, we put `application/json`
        into the `content-type` key so that consumers of the result payload may know how
        to process the data.
        '''
        input_is_json = False
        output_is_json = False
        result = {}
        if 'error_msg' in payload:
            result['error_msg'] = payload['error_msg']
        if 'error_code' in payload:
            result['error_code'] = payload['error_code']

        if 'input_headers_encoded' in payload:
            hdrs = convert_envoy_hdr_msg_to_dict(payload['input_headers_encoded'])
            result['input_headers'] = hdrs
            if Headers.X_HEADER_TASK_ID.lower() in hdrs:
                task_id = hdrs[Headers.X_HEADER_TASK_ID.lower()]
                bpmn_component = workflow.process.component_map[task_id]
                result['failed_task_id'] = task_id
                result['failed_task_name'] = bpmn_component.name
            input_is_json = (hdrs.get('content-type')) == 'application/json'

        if 'input_data_encoded' in payload:
            result['input_data'] = process_data(payload['input_data_encoded'], input_is_json)

        if 'output_headers_encoded' in payload:
            hdrs = convert_envoy_hdr_msg_to_dict(payload['output_headers_encoded'])
            output_is_json = (hdrs.get('content-type')) == 'application/json'
            result['output_headers'] = hdrs

        if 'output_data_encoded' in payload:
            result['output_data'] = process_data(payload['output_data_encoded'], output_is_json)

        self.etcd.put(keys.result, json.dumps(result))
        self.etcd.put(keys.content_type, 'application/json')
