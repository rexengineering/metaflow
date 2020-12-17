from code import app
from flask import request, make_response, jsonify
import os
import requests
from urllib.parse import urlparse
import logging


REXFLOW_XGW_JSONPATH = os.environ['REXFLOW_XGW_JSONPATH']
REXFLOW_XGW_OPERATOR = os.environ['REXFLOW_XGW_OPERATOR']
REXFLOW_XGW_COMPARISON_VALUE = os.environ['REXFLOW_XGW_COMPARISON_VALUE']
REXFLOW_XGW_TRUE_URL = os.environ['REXFLOW_XGW_TRUE_URL']
REXFLOW_XGW_FALSE_URL = os.environ['REXFLOW_XGW_FALSE_URL']
FALSE_ATTEMPTS = int(os.environ['REXFLOW_XGW_FALSE_TOTAL_ATTEMPTS'])
TRUE_ATTEMPTS = int(os.environ['REXFLOW_XGW_TRUE_TOTAL_ATTEMPTS'])
REXFLOW_XGW_FAIL_URL = os.environ['REXFLOW_XGW_FAIL_URL']

SPLITS = REXFLOW_XGW_JSONPATH.split('.')
TRACEID_HEADER = 'x-b3-traceid'

FORWARD_HEADERS = [
    'x-request-id',
    'x-b3-traceid',
    'x-b3-spanid',
    'x-b3-parentspanid',
    'x-b3-sampled',
    'x-b3-flags',
    'x-ot-span-context',
]

TRUE_TASK_ID = os.environ['REXFLOW_TRUE_TASK_ID']
FALSE_TASK_ID = os.environ['REXFLOW_FALSE_TASK_ID']


@app.route('/', methods=['POST'])
def conditional():
    incoming_json = request.json
    value_to_compare = incoming_json  # we will whittle this down to an actual value
    comparison_result = False  # placeholder for scoping

    for split in SPLITS:
        if split in value_to_compare:
            value_to_compare = value_to_compare[split]

    default_val = None
    if type(value_to_compare) == int:
        default_val = int(REXFLOW_XGW_COMPARISON_VALUE)
    else:
        default_val = REXFLOW_XGW_COMPARISON_VALUE

    if type(value_to_compare) in [int, str]:
        if REXFLOW_XGW_OPERATOR == '==':
            comparison_result = (value_to_compare == default_val)
        elif REXFLOW_XGW_OPERATOR == '<':
            comparison_result = (value_to_compare < default_val)
        elif REXFLOW_XGW_OPERATOR == '>':
            comparison_result = (value_to_compare > default_val)
        else:
            raise "invalid rexflow xgw comparison operator"
    else:
        # For now, if the path specified is not a terminal path, we will assume that
        # the comparison failed.
        # TODO: become more sophisticated.
        comparison_result = False

    url = REXFLOW_XGW_TRUE_URL if comparison_result else REXFLOW_XGW_FALSE_URL
    headers = {
        'x-flow-id': request.headers['x-flow-id'],
        'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
        'x-rexflow-task-id': TRUE_TASK_ID if comparison_result else FALSE_TASK_ID
    }
    for h in FORWARD_HEADERS:
        if h in request.headers:
            headers[h] = request.headers[h]

    success = False
    for _ in range(TRUE_ATTEMPTS if comparison_result else FALSE_ATTEMPTS):
        try:
            response = requests.post(url, json=incoming_json, headers=headers)
            response.raise_for_status()
            success = True
            break
        except Exception:
            logging.error(f"failed making a call to {url} on wf {request.headers['x-flow-id']}")

    if not success:
        # Notify Flowd that we failed.
        o = urlparse(url)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        requests.post(REXFLOW_XGW_FAIL_URL, json=incoming_json, headers=headers)

    resp = make_response({"status": 200, "msg": ""})
    if TRACEID_HEADER in request.headers:
        resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER]
    elif TRACEID_HEADER.lower() in request.headers:
        resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER.lower()]
    return resp


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": 200, "msg": ""})
