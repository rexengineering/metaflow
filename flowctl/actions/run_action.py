import argparse
import json
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'run a registered workflow as a workflow instance'


def __refine_args__(parser: argparse.ArgumentParser):
    parser.add_argument(
        '-o',
        '--output',
        action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument(
        '--stopped',
        action='store_true',
        help='flag that all runs should be brought up in the STOPPED state',
    )
    parser.add_argument(
        'workflow_id',
        type=str,
        help='workflow deployment ID to run',
    )
    parser.add_argument(
        '--start_event_id',
        '-s',
        help='Choose between one of many start events to run.'
    )
    parser.add_argument(
        'args',
        nargs='*',
        type=str,
        help='optional arguments to send to the workflow deployment',
    )
    parser.add_argument(
        '--meta',
        '-m',
        type=str,
        help='instance-specific metadata as {key:value[,key:value ...]}'
    )
    return parser

def run_action(namespace: argparse.Namespace, *args, **kws):
    metadata = None
    if namespace.meta is not None:
        m = json.loads(namespace.meta)
        metadata = [
            flow_pb2.StringPair(key=the_key, value=the_value)
            for the_key, the_value in m.items()
        ]

    response = None
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.RunWorkflow(flow_pb2.RunRequest(
            workflow_id=namespace.workflow_id, args=namespace.args,
            stopped=namespace.stopped, start_event_id=namespace.start_event_id,
            metadata=metadata
        ))
    status = response.status
    if status < 0:
        logging.error(
            f'Error from server: {response.status}, "{response.message}"'
        )
    else:
        logging.info(
            f'Got response: {response.status}, "{response.message}", {response.data}'
        )
        if namespace.output:
            print(response.data)
    return status
