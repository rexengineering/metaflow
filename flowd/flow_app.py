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
    X_HEADER_FLOW_ID,
    X_HEADER_WORKFLOW_ID,
    X_HEADER_TOKEN_POOL_ID,
    X_HEADER_TASK_ID,
)

from flowlib import token_api
from flowlib.constants import (
    BStates,
    WorkflowInstanceKeys,
    X_HEADER_FLOW_ID,
    X_HEADER_WORKFLOW_ID,
    X_HEADER_TOKEN_POOL_ID,
)

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


def process_data(data_bytes):
    return base64.b64decode(data_bytes)


class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=['POST'])(self.root_route)
        self.app.route(INSTANCE_FAIL_ENDPOINT_PATH, methods=(['POST']))(self.fail_route)
        self.app.route(WF_MAP_ENDPOINT_PATH, methods=['GET', 'POST'])(self.wf_map)

    async def root_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to completed.
        if X_HEADER_FLOW_ID in request.headers:
            flow_id = request.headers[X_HEADER_FLOW_ID]
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

        if X_HEADER_WORKFLOW_ID not in request.headers or X_HEADER_FLOW_ID not in request.headers:
            return

        flow_id = request.headers[X_HEADER_FLOW_ID]
        wf_id = request.headers[X_HEADER_WORKFLOW_ID]
        timer_pool_id = request.headers.get(X_HEADER_TOKEN_POOL_ID)
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
        wf_map = defaultdict(list)
        for workflow in get_workflows():
            if etcd.get(workflow.keys.state)[0] == BStates.RUNNING:
                wf_id = workflow.process.xmldict['@id']
                wf_did = workflow.id
                wf_map[wf_id].append(wf_did)
        return flow_result(0, 'Ok', wf_map=wf_map)

    def _put_payload(self, payload, keys, workflow):
        if 'input_headers_encoded' in payload:
            hdrs = convert_envoy_hdr_msg_to_dict(payload['input_headers_encoded'])
            self.etcd.put(keys.input_headers, json.dumps(hdrs))
            if X_HEADER_TASK_ID.lower() in hdrs:
                task_id = hdrs[X_HEADER_TASK_ID.lower()]
                bpmn_component = workflow.process.component_map[task_id]
                self.etcd.put(keys.failed_task, bpmn_component.name)
        if 'input_data_encoded' in payload:
            self.etcd.put(keys.input_data, process_data(payload['input_data_encoded']))
        if 'output_data_encoded' in payload:
            self.etcd.put(keys.output_data, process_data(payload['output_data_encoded']))
        if 'output_headers_encoded' in payload:
            hdrs = convert_envoy_hdr_msg_to_dict(payload['output_headers_encoded'])
            self.etcd.put(keys.output_headers, json.dumps(hdrs))
        if 'error_code' in payload:
            self.etcd.put(keys.error_code, payload['error_code'])
        if 'error_msg' in payload:
            self.etcd.put(keys.error_message, payload['error_msg'])
