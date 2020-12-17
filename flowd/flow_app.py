import logging

from quart import request
import json

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp
from flowlib.constants import BStates, WorkflowInstanceKeys
from flowlib.workflow import Workflow


class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=('POST',))(self.root_route)
        self.app.route('/instancefail', methods=('POST',))(self.fail_route)

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
                        incoming_data = await request.data
                        try:
                            self.etcd.put(payload_key, incoming_data)
                            self.etcd.put(headers_key, json.dumps(
                                {h: request.headers[h] for h in request.headers.keys()}
                            ).encode())
                            transition_state(
                                self.etcd, state_key, [BStates.STOPPING], BStates.STOPPED
                            )
                        except Exception as exn:
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
