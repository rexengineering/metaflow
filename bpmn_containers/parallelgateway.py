import json
import logging
import os
from typing import Any

from flask import Flask, request, make_response
import requests

from flowlib import connectors, executor
from flowlib.constants import flow_result, Headers, Parallel


app = Flask(__name__)


def post(target: str, response: Any) -> None:
    responses_response = requests.post(target, headers=response.headers, data=response.data)
    responses_response.raise_for_status()


def make_connector() -> connectors.Connector:
    mode = Parallel.MergeModes(int(os.getenv(Parallel.GatewayVars.MERGE_MODE, 1)))
    in_ids = json.loads(os.getenv(Parallel.GatewayVars.INCOMING_IDS, '[]'))
    in_urls = json.loads(os.getenv(Parallel.GatewayVars.INCOMING_URLS, '[]'))
    out_ids = json.loads(os.getenv(Parallel.GatewayVars.FORWARD_IDS, '[]'))
    out_urls = json.loads(os.getenv(Parallel.GatewayVars.FORWARD_URLS, '[]'))
    in_edges = [connectors.Connection(in_id, in_url, None) for in_id, in_url in zip(in_ids, in_urls)]
    # TODO: Use the HTTP method appropriate to each destination.
    out_edges = [connectors.Connection(out_id, out_url, 'POST') for out_id, out_url in zip(out_ids, out_urls)]
    return connectors.ParallelConnector(in_edges, out_edges, {'post': post}, mode)


connector = make_connector()
connector_executor = executor.get_executor()

def handle_data(request):
    try:
        connector.handle_data(request)
    except connectors.ConnectorError as exn:
        # TODO: Mark a fault as occurring here in the workflow and transition to ERROR state.
        logging.exception('One or more errors occurred while handling response(s).', exc_info=exn)


@app.route('/', methods=['POST'])
def parallel():
    if connector.is_valid(request):
        connector_executor.submit(handle_data, request)
        resp = make_response(flow_result(0, 'Ok'), 202)
    else:
        # TODO: Mark a fault as occurring here in the workflow and transition to ERROR state.
        resp = make_response(flow_result(-1, 'Invalid input'), 400)

    if Headers.TRACEID_HEADER in request.headers:
        resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
    elif Headers.TRACEID_HEADER.lower() in request.headers:
        resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER.lower()]

    return resp


@app.route('/', methods=['GET'])
def health():
    return flow_result(0, 'Ok')


if __name__ == '__main__':
    app.run()
