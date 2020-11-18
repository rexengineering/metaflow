import logging

from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp

import json

def header_to_dict(headers):
    return {h: headers[h] for h in headers.keys()}

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
                    payload = self.etcd.get(f'{key_prefix}/payload')
                    if payload[0]:
                        self.etcd.delete(f'{key_prefix}/payload')
                        self.etcd.delete(f'{key_prefix}/headers')
                        self.etcd.put(f'{key_prefix}/wasError', b'TRUE')

                    self.etcd.put(f'{key_prefix}/result', await request.data)
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                         ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'

    async def fail_route(self):
        print("we just tried to 'mobilize chewanintierationalofofadapressure'", flush=True)
        # When there is a flow ID in the headers, store the result in etcd and
        # change the state to ERROR.
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
                        self.etcd.put(f'{key_prefix}/headers', json.dumps(header_to_dict(request.headers)).encode())
                    except:
                        import traceback; traceback.print_exc()
                        print("well that was bad", flush=True)
                else:
                    logging.error(
                        f'Race on {state_key}; state changed out of known'
                         ' good state before state transition could occur!'
                    )
        return 'Hello there!\n'
