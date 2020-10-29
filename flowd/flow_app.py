import logging

from quart import request

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp

class FlowApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=('POST',))(self.root_route)

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
