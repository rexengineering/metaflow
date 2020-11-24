import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

__help__ = 'remove a workflow and its related microservices from the system'


def __refine_args__(parser : argparse.ArgumentParser):
    # it gets very boring typing out the KIND types, so defining some useful shorthands
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-k', '--kind', action='store', default='',
        help=f'Request kind, one of {", ".join(key for key in flow_pb2.RequestKind.keys())}, default is INSTANCE.',
    )
    group.add_argument('-d', '--deployment', action='store_true',
        help=f'Shorthand to specify kind of type DEPLOYMENT.',
    )
    group.add_argument('-i', '--instance', action='store_true',
        help=f'Shorthand to specify kind of type INSTANCE.',
    )
    # expand group with additional shorthands for new KIND types

    parser.add_argument('ids', nargs='+', type=str,
        help='Specific workflow deployment or instance ID\'s to delete.'
    )
    return parser


def delete_action (namespace : argparse.Namespace, *args, **kws):
    response = None
    if namespace.deployment:
        kind = flow_pb2.RequestKind.DEPLOYMENT
    elif namespace.instance:
        kind = flow_pb2.RequestKind.INSTANCE
    else:
        kind = getattr(flow_pb2.RequestKind, namespace.kind, flow_pb2.RequestKind.INSTANCE)
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.DeleteWorkflow(flow_pb2.DeleteRequest(
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
