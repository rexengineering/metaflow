import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'Update a workflow deployment. Currently supports setting ingress for start events.'


def __refine_args__(parser: argparse.ArgumentParser):
    parser.add_argument('wf_id', help='Workflow Deployment ID to update.')
    parser.add_argument(
        '--action', action='store', default='expose_ingress',
        help=f"Action kind, one of {', '.join(k for k in flow_pb2.UpdateRequestAction.keys())}")  # noqa
    parser.add_argument(
        '--set', action='append',
        help='Substitution arguments to format the Ingress Template.'
    )
    parser.add_argument(
        '--host', action='store',
        help='Host at which to expose the WF.',
    )
    parser.add_argument(
        '--force_switch_from', help='Forcefully switch the ingress from provided workflow id.'
    )
    return parser


def update_action(namespace: argparse.Namespace, *args, **kws):
    response = None
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.UpdateWorkflow(flow_pb2.UpdateRequest(
            action=namespace.action, wf_id=namespace.wf_id, host=namespace.host,
            switch_from_wf_id=namespace.force_switch_from, args=namespace.set,
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
