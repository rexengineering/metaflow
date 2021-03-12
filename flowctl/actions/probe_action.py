import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'force health check probe on all workflows (default) or specified workflow ID\'s'


def __refine_args__(parser: argparse.ArgumentParser):

    parser.add_argument(
        '-o',
        '--output',
        action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument(
        'ids',
        nargs='*',
        type=str,
        help='Specific workflow deployment ID\'s to probe.'
    )
    return parser


def probe_action(namespace: argparse.Namespace, *args, **kws):
    response = None
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        request = flow_pb2.ProbeRequest(
            ids=namespace.ids
        )
        response = flowd.ProbeWorkflow(request)
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
