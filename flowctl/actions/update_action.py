import argparse
import logging

import yaml

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'Update a workflow deployment. Currently supports setting ingress for start events.'


def __refine_args__(parser: argparse.ArgumentParser):
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


def update_action(namespace: argparse.Namespace, *args, **kws):
    responses = dict()
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        for spec in namespace.bpmn_spec:
            with open(spec, 'r') as spec_file_obj:
                responses[spec] = flowd.UpdateWorkflow(
                    flow_pb2.UpdateRequest(
                        update_spec=spec_file_obj.read()
                    )
                )
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
