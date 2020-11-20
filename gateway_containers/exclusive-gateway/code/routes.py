from code import app
from flask import request
import os
import requests
from urllib.parse import urlparse


REXFLOW_XGW_JSONPATH = os.environ['REXFLOW_XGW_JSONPATH']
REXFLOW_XGW_OPERATOR = os.environ['REXFLOW_XGW_OPERATOR']
REXFLOW_XGW_COMPARISON_VALUE = os.environ['REXFLOW_XGW_COMPARISON_VALUE']
REXFLOW_XGW_TRUE_URL = os.environ['REXFLOW_XGW_TRUE_URL']
REXFLOW_XGW_FALSE_URL = os.environ['REXFLOW_XGW_FALSE_URL']
REXFLOW_XGW_FALSE_TOTAL_ATTEMPTS = int(os.environ['REXFLOW_XGW_FALSE_TOTAL_ATTEMPTS'])
REXFLOW_XGW_TRUE_TOTAL_ATTEMPTS = int(os.environ['REXFLOW_XGW_TRUE_TOTAL_ATTEMPTS'])
REXFLOW_XGW_FAIL_URL = os.environ['REXFLOW_XGW_FAIL_URL']

SPLITS = REXFLOW_XGW_JSONPATH.split('.')

@app.route('/', methods=['POST'])
def conditional():
    incoming_json = request.json
    value_to_compare = incoming_json  # we will whittle this down to an actual value
    comparison_result = False  # placeholder for scoping

    for split in SPLITS:
        if split in value_to_compare:
            value_to_compare = value_to_compare[split]

    default_val = int(REXFLOW_XGW_COMPARISON_VALUE) if type(value_to_compare) == int else REXFLOW_XGW_COMPARISON_VALUE
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
    }
    if 'x-b3-spanid' in request.headers:
        headers['x-b3-spanid'] = request.headers['x-b3-spanid']

    success = False
    for _ in range(REXFLOW_XGW_TRUE_TOTAL_ATTEMPTS if comparison_result else REXFLOW_XGW_FALSE_TOTAL_ATTEMPTS):
        try:
            response = requests.post(url, json=incoming_json, headers=headers)
            response.raise_for_status()
            success = True
            break
        except Exception:
            print(f"failed making a call to {url} on wf {request.headers['x-flow-id']}", flush=True)

    if not success:
        # Notify Flowd that we failed.
        o = urlparse(url)
        headers['x-rexflow-original-host'] = o.netloc
        headers['x-rexflow-original-path'] = o.path
        requests.post(REXFLOW_XGW_FAIL_URL, json=incoming_json, headers=headers)

    return "The faith of knowing deep inside your heart, that Heaven holds"


@app.route('/', methods=['GET'])
def health():
    return "more than just some stars...Someone's up there watching over you"
