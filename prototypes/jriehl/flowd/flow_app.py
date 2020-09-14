import logging

from flask import Flask, jsonify, request

from flowlib.etcd_utils import get_etcd, transition_state


app = Flask(__name__)

etcd = get_etcd()


@app.route('/', methods=('POST',))
def root_route():
    # When there is a flow ID in the headers, store the result in etcd and
    # change the state to completed.
    if 'X-Flow-Id' in request.headers:
        flow_id = request.headers['X-Flow-Id']
        key_prefix = f'/rexflow/instances/{flow_id}'
        state_key = f'{key_prefix}/state'
        good_states = {b'STARTING', b'RUNNING'}
        if etcd.get(state_key)[0] in good_states:
            if transition_state(etcd, state_key, good_states, b'COMPLETED'):
                etcd.put(f'{key_prefix}/result', request.data)
            else:
                logging.error(f'Race on {state_key}; state changed out of known'\
                               ' good state before state transition could occur!')
    return 'Hello there!\n'
