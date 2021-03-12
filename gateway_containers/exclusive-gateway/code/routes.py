from code import app
from flask import request, make_response, jsonify
import json
import logging
import os
import requests
from urllib.parse import urlparse


CONDITIONAL_PATHS = json.loads(os.environ['REXFLOW_XGW_CONDITIONAL_PATHS'])
DEFAULT_PATH = json.loads(os.environ['REXFLOW_XGW_DEFAULT_PATH'])
REXFLOW_XGW_FAIL_URL = os.environ['REXFLOW_XGW_FAIL_URL']
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)

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

DMN_SERVER_HOST = os.getenv("DMN_SERVER_HOST", "http://dmnserver.rexflow:8001")


@app.route('/', methods=['POST'])
def conditional():
    req_json = request.json
    total_attempts = None
    target_url = None
    target_component_id = None

    # For now, the following loop just iterates over one item (since we haven't yet
    # worked with Jon to figure out how to support multiple outgoing branches in
    # a single XGW).
    for path in CONDITIONAL_PATHS:
        if path['type'] == 'python':
            if eval(path['expression']):
                total_attempts = path['total_attempts']
                target_url = path['k8s_url']
                target_component_id = path['component_id']
                break
        elif path['type'] == 'feel':
            headers = {'Content-type' : 'application/json'}
            dataz = [{path['expression'] : "True", "":"False"}, req_json]

            # TODO: move this hardcoded uri to somwhere configurations live
            response = requests.post(
                f"{DMN_SERVER_HOST}/dmn/dt",
                headers=headers, 
                data=json.dumps(dataz)
            )

            if response.json()[0]['result'] == "True":
                total_attempts = path['total_attempts']
                target_url = path['k8s_url']
                target_component_id = path['component_id']
                break
        else:
            assert False, "unsupported expression type."

    if not target_url and not total_attempts and not target_component_id:
        total_attempts = DEFAULT_PATH['total_attempts']
        target_url = DEFAULT_PATH['k8s_url']
        target_component_id = DEFAULT_PATH['component_id']

    headers = {
        'x-flow-id': request.headers['x-flow-id'],
        'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
        'x-rexflow-task-id': target_component_id,
    }
    for h in FORWARD_HEADERS:
        if h in request.headers:
            headers[h] = request.headers[h]

    success = False
    for _ in range(int(total_attempts)):
        try:
            response = requests.post(target_url, json=req_json, headers=headers)
            response.raise_for_status()
            success = True
            break
        except Exception:
            logging.error(
                f"failed making a call to {target_url} on wf {request.headers['x-flow-id']}"
            )

    o = urlparse(target_url)
    headers['x-rexflow-original-host'] = o.netloc
    headers['x-rexflow-original-path'] = o.path

    if not success:
        # Notify Flowd that we failed.
        requests.post(REXFLOW_XGW_FAIL_URL, json=req_json, headers=headers)

    if KAFKA_SHADOW_URL:
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
