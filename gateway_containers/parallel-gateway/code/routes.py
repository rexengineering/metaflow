

import json
import os
import requests

from flask import request, make_response, jsonify

from . import app

from flowlib.constants import Headers


FORWARD_HEADERS = [
    'x-request-id',
    'x-b3-traceid',
    'x-b3-spanid',
    'x-b3-parentspanid',
    'x-b3-sampled',
    'x-b3-flags',
    'x-ot-span-context',
]


REXFLOW_PGW_TYPE = os.getenv('REXFLOW_PGW_TYPE', "")
REXFLOW_PGW_INCOMING_COUNT = int(os.getenv('REXFLOW_PGW_INCOMING_COUNT', 0))
REXFLOW_PGW_FORWARD_URL = os.getenv('REXFLOW_PGW_FORWARD_URL', "")
REXFLOW_PGW_FORWARD_ID = os.getenv('REXFLOW_PGW_FORWARD_ID', "")
REXFLOW_PGW_FORWARD_URLS = os.getenv('REXFLOW_PGW_FORWARD_URLS', "")
REXFLOW_PGW_FORWARD_IDS = os.getenv('REXFLOW_PGW_FORWARD_IDS', "")

if REXFLOW_PGW_FORWARD_URLS:
    REXFLOW_PGW_FORWARD_URLS = json.loads(REXFLOW_PGW_FORWARD_URLS)

if REXFLOW_PGW_FORWARD_IDS:
    REXFLOW_PGW_FORWARD_IDS = json.loads(REXFLOW_PGW_FORWARD_IDS)

REXFLOW_PGW_FORWARD_URLS = REXFLOW_PGW_FORWARD_URLS or []
REXFLOW_PGW_FORWARD_IDS = REXFLOW_PGW_FORWARD_IDS or []


pending_flows = {}


@app.route('/', methods=['POST'])
def parallel():
    incoming_json = request.json

    headers = {
        'x-flow-id': request.headers['x-flow-id'],
        'x-rexflow-wf-id': request.headers['x-rexflow-wf-id'],
    }

    for h in FORWARD_HEADERS:
        if h in request.headers:
            headers[h] = request.headers[h]

    if REXFLOW_PGW_TYPE == "splitter":

        assert len(REXFLOW_PGW_FORWARD_URLS) == len(REXFLOW_PGW_FORWARD_IDS), \
            f"Lengths of REXFLOW_PGW_FORWARD_URLS and REXFLOW_PGW_FORWARD_IDS differ: {len(REXFLOW_PGW_FORWARD_URLS)} {len(REXFLOW_PGW_FORWARD_IDS)}"

        for i in range(len(REXFLOW_PGW_FORWARD_URLS)):
            headers['x-rexflow-task-id'] = REXFLOW_PGW_FORWARD_IDS[i]
            requests.post(REXFLOW_PGW_FORWARD_URLS[i], json=incoming_json, headers=headers)

    elif REXFLOW_PGW_TYPE == "combiner":

        flow_id = request.headers['x-flow-id']

        if flow_id not in pending_flows:
            pending_flows[flow_id] = []

        results = pending_flows[flow_id]
        results.append(incoming_json)

        pending_count = REXFLOW_PGW_INCOMING_COUNT - len(results)

        if pending_count == 0:

            if REXFLOW_PGW_FORWARD_URL:
                headers['x-rexflow-task-id'] = REXFLOW_PGW_FORWARD_ID
                requests.post(REXFLOW_PGW_FORWARD_URL, json=incoming_json, headers=headers)
            else:
                logging.error(f"[flow_id={flow_id}] REXFLOW_PGW_FORWARD_URL not set, can't send results.")

            del pending_flows[flow_id]

        else:
            logging.info(f"[flow_id={flow_id}] Still waiting for {pending_count} results.")

    else:
        logging.error(f"REXFLOW_PGW_TYPE == '{REXFLOW_PGW_TYPE}'???")

    resp = make_response({"status": 200, "msg": ""})

    if Headers.TRACEID_HEADER in request.headers:
        resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
    elif Headers.TRACEID_HEADER.lower() in request.headers:
        resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER.lower()]

    return resp


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": 200, "msg": ""})

