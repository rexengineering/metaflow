import argparse
import json
import logging
import pprint

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'query workflows or workflow instances'


def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('-k', '--kind', action='store', default='',
        help=f'Request kind, one of {", ".join(key for key in flow_pb2.RequestKind.keys())}, default is INSTANCE.',
    )
    parser.add_argument('-o', '--output', action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument('ids', nargs='*', type=str,
        help='Specific workflow deployment or instance ID\'s to query.'
    )
    return parser


def ps_action (namespace : argparse.Namespace, *args, **kws):
    response = None
    kind = getattr(flow_pb2.RequestKind, namespace.kind, flow_pb2.RequestKind.INSTANCE)
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        request = flow_pb2.PSRequest(
            kind=kind, ids=namespace.ids
        )
        response = flowd.PSQuery(request)
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
