from code import app
from flask import request, make_response, jsonify
import logging
import os
import requests
from urllib.parse import urlparse
import logging


REXFLOW_XGW_EXPRESSION = os.environ['REXFLOW_XGW_EXPRESSION']
REXFLOW_XGW_TRUE_URL = os.environ['REXFLOW_XGW_TRUE_URL']
REXFLOW_XGW_FALSE_URL = os.environ['REXFLOW_XGW_FALSE_URL']
FALSE_ATTEMPTS = int(os.environ['REXFLOW_XGW_FALSE_TOTAL_ATTEMPTS'])
TRUE_ATTEMPTS = int(os.environ['REXFLOW_XGW_TRUE_TOTAL_ATTEMPTS'])
REXFLOW_XGW_FAIL_URL = os.environ['REXFLOW_XGW_FAIL_URL']
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", "http://kafka-shadow.rexflow:5000/")

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
    req_json = request.json
    comparison_result = eval(REXFLOW_XGW_EXPRESSION)

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
            response = requests.post(url, json=req_json, headers=headers)
            response.raise_for_status()
            success = True
            break
        except Exception:
            logging.error(f"failed making a call to {url} on wf {request.headers['x-flow-id']}")

    o = urlparse(url)
    headers['x-rexflow-original-host'] = o.netloc
    headers['x-rexflow-original-path'] = o.path
    
    if not success:
        # Notify Flowd that we failed.
        requests.post(REXFLOW_XGW_FAIL_URL, json=req_json, headers=headers)

    try:
        headers['x-rexflow-failure'] = True
        requests.post(KAFKA_SHADOW_URL, headers=headers, json=req_json).raise_for_status()
    except Exception:
        logging.warning("Failed shadowing traffic to Kafka")

    resp = make_response({"status": 200, "msg": ""})
    if TRACEID_HEADER in request.headers:
        resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER]
    elif TRACEID_HEADER.lower() in request.headers:
        resp.headers[TRACEID_HEADER] = request.headers[TRACEID_HEADER.lower()]
    return resp


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": 200, "msg": ""})
