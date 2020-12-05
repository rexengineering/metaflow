import logging

from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp
from flowlib.constants import BStates, WorkflowInstanceKeys

import json


def header_to_dict(headers):
    return {h: headers[h] for h in headers.keys()}


class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        # self.app.route('/', methods=('POST',))(self.root_route)
        self.app.route('/instancefail', methods=('POST',))(self.fail_route)

    async def fail_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to ERROR.
        if 'X-Flow-Id' in request.headers:
            flow_id = request.headers['X-Flow-Id']

            state_key = WorkflowInstanceKeys.state_key(flow_id)
            payload_key = WorkflowInstanceKeys.payload_key(flow_id)
            headers_key = WorkflowInstanceKeys.headers_key(flow_id)

            good_states = {BStates.STARTING, BStates.RUNNING}
            if self.etcd.get(state_key)[0] in good_states:
                if transition_state(self.etcd, state_key, good_states, b'ERROR'):
                    incoming_json = await request.get_json()
                    try:
                        self.etcd.put(payload_key, json.dumps(incoming_json).encode())
                        self.etcd.put(
                            headers_key,
                            json.dumps(header_to_dict(request.headers)).encode()
                        )
                    except Exception:
                        logging.error(f"Was unable to save the data for flow_id {flow_id}.")
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                        ' good state before state transition could occur!'
                    )
        return 'Another happy landing (:'
