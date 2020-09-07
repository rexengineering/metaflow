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
        etcd.put(f'{key_prefix}/result', request.data)
        transition_state(etcd, f'{key_prefix}/state', [b'STARTING', b'RUNNING'],
                         b'COMPLETED')
    return 'Hello there!\n'
