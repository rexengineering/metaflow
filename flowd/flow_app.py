import asyncio
from collections import defaultdict
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
)
from flowlib import token_api

TIMEOUT_SECONDS = 10


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
                    payload = self.etcd.get(keys.payload)
                    if payload[0]:
                        self.etcd.delete(keys.headers)
                        self.etcd.delete(keys.payload)
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
        if X_HEADER_WORKFLOW_ID in request.headers and X_HEADER_FLOW_ID in request.headers:
            flow_id = request.headers[X_HEADER_FLOW_ID]
            wf_id = request.headers[X_HEADER_WORKFLOW_ID]
            timer_pool_id = request.headers.get(X_HEADER_TOKEN_POOL_ID)
            workflow = Workflow.from_id(wf_id)
            state_key = WorkflowInstanceKeys.state_key(flow_id)
            good_states = {BStates.STARTING, BStates.RUNNING}

            if self.etcd.get(state_key)[0] in good_states:
                if not workflow.process.properties.is_recoverable:
                    logging.info("Transition to ERROR")
                    if timer_pool_id is None or token_api.token_fail(timer_pool_id):
                        if not transition_state(self.etcd, state_key, good_states, BStates.ERROR):
                            logging.error(
                                f'Race on {state_key}; state changed out of known'
                                ' good state before state transition could occur!'
                            )

                else:
                    payload_key = WorkflowInstanceKeys.payload_key(flow_id)
                    headers_key = WorkflowInstanceKeys.headers_key(flow_id)

                    if transition_state(self.etcd, state_key, good_states, b'STOPPING'):
                        try:
                            self.etcd.put(headers_key, json.dumps(
                                {h: request.headers[h] for h in request.headers.keys()}
                            ).encode())
                            with timeout(TIMEOUT_SECONDS):
                                incoming_data = await request.data
                            self.etcd.put(payload_key, incoming_data)
                            transition_state(
                                self.etcd, state_key, [BStates.STOPPING], BStates.STOPPED
                            )
                        except asyncio.exceptions.TimeoutError as exn:
                            self.etcd.put(state_key, BStates.ERROR)
                            if timer_pool_id:
                                token_api.token_fail(timer_pool_id)
                            logging.exception(
                                f"Timed out waiting for payload on flow {flow_id}",
                                exc_info=exn,
                            )
                        except Exception as exn:
                            self.etcd.put(state_key, BStates.ERROR)
                            if timer_pool_id:
                                token_api.token_fail(timer_pool_id)
                            logging.exception(
                                f"Was unable to save the data for flow_id {flow_id}.",
                                exc_info=exn,
                            )
                    else:
                        logging.error(
                            f'Race on {state_key}; state changed out of known'
                            ' good state before state transition could occur!'
                        )
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
