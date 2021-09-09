import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

__help__ = 'validate sufficiently annotated BPMN file(s)'


def __refine_args__(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--include_kubernetes',
        action='store_true',
        help='Include compiled k8s specs for all deployments.',
    )
    parser.add_argument(
        '-o',
        '--output',
        action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument(
        'bpmn_spec',
        nargs='+',
        help='sufficiently annotated BPMN file(s)'
    )
    return parser


def grpc_validate(namespace: argparse.Namespace):
    '''grpc_validate(namespace)
    Arguments:
        namespace: argparse.Namespace - Argument map of command line inputs
    Returns map from specification file names to GPRC response data.
    '''
    responses = dict()
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        for spec in namespace.bpmn_spec:
            with open(spec, 'rb') as spec_file_obj:
                responses[spec] = flowd.ValidateWorkflow(
                    flow_pb2.ValidateRequest(
                        bpmn_xml=spec_file_obj.read(),
                        include_kubernetes=namespace.include_kubernetes
                    )
                )
    return responses


def validate_action(namespace: argparse.Namespace, *args, **kws):
    '''apply_action(namespace)
    Arguments:
        namespace: argparse.Namespace - Argument map of command line inputs
    Returns toplevel exit code.
    '''
    responses = grpc_validate(namespace)
    status = 0
    for spec, response in responses.items():
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
            if namespace.output:
                print(response.data)
    return status
