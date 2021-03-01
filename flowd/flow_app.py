import asyncio
import logging
import json

from async_timeout import timeout
from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp
from flowlib.constants import BStates, WorkflowInstanceKeys
from flowlib.workflow import Workflow

from flowlib.config import INSTANCE_FAIL_ENDPOINT_PATH


TIMEOUT_SECONDS = 10


class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=('POST',))(self.root_route)
        self.app.route(INSTANCE_FAIL_ENDPOINT_PATH, methods=('POST',))(self.fail_route)

    async def root_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to completed.
        if 'X-Flow-Id' in request.headers:
            flow_id = request.headers['X-Flow-Id']
            state_key = WorkflowInstanceKeys.state_key(flow_id)
            payload_key = WorkflowInstanceKeys.payload_key(flow_id)
            was_error_key = WorkflowInstanceKeys.was_error_key(flow_id)
            headers_key = WorkflowInstanceKeys.headers_key(flow_id)
            good_states = {BStates.STARTING, BStates.RUNNING}
            if self.etcd.get(state_key)[0] in good_states:
                if transition_state(self.etcd, state_key, good_states, BStates.COMPLETED):
                    payload = self.etcd.get(payload_key)
                    if payload[0]:
                        self.etcd.delete(headers_key)
                        self.etcd.delete(payload_key)
                        self.etcd.put(was_error_key, BStates.TRUE)
                    self.etcd.put(WorkflowInstanceKeys.result_key(flow_id), await request.data)
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                        ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'

    async def fail_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to ERROR.
        if 'X-Rexflow-Wf-Id' in request.headers and 'X-Flow-Id' in request.headers:
            flow_id = request.headers['X-Flow-Id']
            wf_id = request.headers['X-Rexflow-Wf-Id']
            workflow = Workflow.from_id(wf_id)
            state_key = WorkflowInstanceKeys.state_key(flow_id)
            good_states = {BStates.STARTING, BStates.RUNNING}

            if self.etcd.get(state_key)[0] in good_states:
                if not workflow.process.properties.is_recoverable:
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
                            logging.exception(
                                f"Timed out waiting for payload on flow {flow_id}",
                                exc_info=exn,
                            )
                        except Exception as exn:
                            self.etcd.put(state_key, BStates.ERROR)
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
