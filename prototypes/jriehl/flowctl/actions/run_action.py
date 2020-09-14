import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'run a registered workflow as a workflow instance'

def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('-o', '--output', action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument('--stopped', action='store_true',
        help='flag that all runs should be brought up in the STOPPED state',
    )
    parser.add_argument('workflow_id', type=str,
        help='workflow deployment ID to run',
    )
    parser.add_argument('args', nargs='*', type=str,
        help='optional arguments to send to the workflow deployment',
    )
    return parser

def run_action(namespace : argparse.Namespace, *args, **kws):
    response = None
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.RunWorkflow(flow_pb2.RunRequest(
            workflow_id=namespace.workflow_id, args=namespace.args,
            stopped=namespace.stopped,
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
