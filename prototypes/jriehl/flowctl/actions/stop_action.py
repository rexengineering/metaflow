import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'stop one or more workflow deployments or instances'


def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('-k', '--kind', action='store', default='INSTANCE',
        help=f'Request kind, one of {", ".join(key for key in flow_pb2.RequestKind.keys())}, default is INSTANCE.',
    )
    parser.add_argument('ids', nargs='+', help='workflow id\'s to stop')
    return parser


def stop_action(namespace : argparse.Namespace, *args, **kws):
    response = None
    kind = getattr(flow_pb2.RequestKind, namespace.kind, flow_pb2.RequestKind.INSTANCE)
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.StopWorkflow(flow_pb2.StopRequest(
            kind=kind, ids=namespace.ids
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
    return status
