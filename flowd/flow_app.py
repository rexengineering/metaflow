import logging

from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp

import json

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
            key_prefix = f'/rexflow/instances/{flow_id}'
            state_key = f'{key_prefix}/state'
            good_states = {b'STARTING', b'RUNNING'}
            if self.etcd.get(state_key)[0] in good_states:
                if transition_state(self.etcd, state_key, good_states, b'COMPLETED'):
                    self.etcd.put(f'{key_prefix}/result', await request.data)
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                         ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'

    def _get_relevant_headers(self, headers):
        out = {}
        for k in headers.keys():
            out[k] = headers[k]
        from pprint import pprint as pp
        pp(out)
        print("*", flush=True)
        return out

    async def fail_route(self):
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to ERROR.
        print("asdfasdlkfjas;ldkfjasl;kdjfakl;sjfkl;asdj;lfkasjd" , flush=True)
        if 'X-Flow-Id' in request.headers:
            flow_id = request.headers['X-Flow-Id']
            key_prefix = f'/rexflow/instances/{flow_id}'
            state_key = f'{key_prefix}/state'
            good_states = {b'STARTING', b'RUNNING'}
            if self.etcd.get(state_key)[0] in good_states:
                if transition_state(self.etcd, state_key, good_states, b'ERROR'):
                    incoming_json = await request.get_json()
                    try:
                        self.etcd.put(f'{key_prefix}/payload', json.dumps(incoming_json).encode())
                        self.etcd.put(f'{key_prefix}/headers', json.dumps(self._get_relevant_headers(request.headers)).encode())
                        # self.etcd.put(f'{key_prefix}/failedstep', request.headers.get('x-rexflow-task-name', 'unknown').encode())
                    except:
                        import traceback; traceback.print_exc()
                        print("well that was bad", flush=True)
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                         ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'
