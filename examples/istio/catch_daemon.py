import asyncio
import logging
import signal
from typing import Any

import boto3
from botocore.exceptions import ClientError
import json
import os
import re
import requests
import time

from quart import jsonify

QUEUE = 'stolenpants'
FORWARD_QUEUE = 'saucedpants'

kinesis_client = None # boto3.client('kinesis', region_name='us-west-2')
stream_info = None #kinesis_client.describe_stream(StreamName=QUEUE)['StreamDescription']

running = None #True
shard_it = None #None


def get_iterator(shard):
    global shard_it
    if shard_it:
        return shard_it
    shard_id = shard['ShardId']
    resp = kinesis_client.get_shard_iterator(
        StreamName=QUEUE,
        ShardId=shard_id,
        ShardIteratorType='LATEST',
    )
    shard_it = resp['ShardIterator']
    return shard_it

def get_events():
    # This is a toy demo prototype since we are not going to be using Kinesis in our
    # production system. Therefore, I do not bother with the Kinesis-specific work of
    # coordinating between multiple readers of the same queue.
    global shard_it
    
    while True:  # iterate through all records in stream
        if not running:
            break
        response = kinesis_client.get_records(
            ShardIterator=get_iterator(stream_info['Shards'][0]),  # assume only 1 shard for now
            Limit=1000,
        )
        for record in response['Records']:
            print(record, flush=True)
            yield record
        shard_it = response['NextShardIterator']
        if shard_it is None or response['MillisBehindLatest'] == 0:
            break
        time.sleep(1)

if __name__ == "__main__":
    kinesis_client = boto3.client('kinesis', region_name='us-west-2')
    stream_info = kinesis_client.describe_stream(StreamName=QUEUE)['StreamDescription']
    forward_stream_info = kinesis_client.describe_stream(StreamName=FORWARD_QUEUE)['StreamDescription']

    running = True
    shard_it = None

    while True:
        for event in get_events():
            the_json = json.loads(event['Data'])
            print(the_json)
            sauce = input("What type of sauce? ")
            the_json['sauce'] = sauce
            kinesis_client.put_record(
                StreamName=FORWARD_QUEUE,
                Data=json.dumps(the_json).encode('utf-8'),
                PartitionKey="1234567890",
            )
        time.sleep(1)
