import boto3
import json
from code import app
from flask import request
import os
import requests


QUEUE = os.environ['REXFLOW_THROWGATEWAY_QUEUE']
FORWARD_URL = os.getenv('REXFLOW_THROWGATEWAY_FORWARD_URL', '')

kinesis_client = boto3.client('kinesis', region_name='us-west-2')


def send_to_stream(incoming_json, flow_id, wf_id):
    cp = incoming_json.copy()
    cp['x-flow-id'] = flow_id
    cp['x-rexflow-wf-id'] = wf_id
    kinesis_client.put_record(
        StreamName=QUEUE,
        Data=json.dumps(cp).encode('utf-8'),
        PartitionKey=str(flow_id),  # For now, the partition key doesn't really matter.
    )


@app.route('/', methods=['POST'])
def throw_event():
    incoming_json = request.json
    send_to_stream(incoming_json, request.headers['x-flow-id'], request.headers['x-rexflow-wf-id'])
    if FORWARD_URL:
        requests.post(
            FORWARD_URL,
            headers={'x-flow-id': request.headers['x-flow-id'], 'x-rexflow-wf-id': request.headers['x-rexflow-wf-id']},
            json=incoming_json,
        )
    return "For my ally is the Force, and a powerful ally it is."


@app.route('/', methods=['GET'])
def health():
    return "May the Force be with you."
