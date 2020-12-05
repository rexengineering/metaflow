import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

__help__ = 'restart a wf instance in the error state'


def __refine_args__(parser: argparse.ArgumentParser):
    parser.add_argument('wf_instance_id', help='workflow instance id to restart')
    return parser


def restart_action(namespace: argparse.Namespace, *args, **kws):
    '''retry_action(namespace)
    Arguments:
        namespace : argparse.Namespace - Argument map of command line inputs
    Returns toplevel exit code.
    '''
    response = None
    wf_instance_id = namespace.wf_instance_id

    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.RestartWorkflow(flow_pb2.RestartRequest(
            wf_instance_id=wf_instance_id
        ))

    status = 0
    if response.status < 0:
        logging.error(
            f'Error from server: {response.status}, "{response.message}"'
        )
        if status >= 0:
            status = response.status
    else:
        logging.info(
            f'Got response: {response.status}, "{response.message}", {response.data}'
        )
    print(response.data, flush=True)
    return status
