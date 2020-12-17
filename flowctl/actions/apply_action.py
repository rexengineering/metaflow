import argparse
import logging

import xmltodict

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

__help__ = 'apply sufficiently annotated BPMN file(s)'


def __refine_args__(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--stopped',
        action='store_true',
        help='flag that all deployments should be brought up in the STOPPED state',
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


def process_specification(specification):
    '''process_specification(specification)
    Given a BPMN specification (this can either be a file or string), perform
    rudimentary validation and cleanup of the document.  Returns a string with
    the resulting XML.
    '''
    spec = xmltodict.parse(specification)
    definition = spec['bpmn:definitions']
    definition_child_count = len([key for key in definition if key[0] != '@'])
    assert definition_child_count == 2, \
        f'Unexpected child count (got {definition_child_count}, not 2).'
    return xmltodict.unparse(spec)


def apply_action(namespace: argparse.Namespace, *args, **kws):
    '''apply_action(namespace)
    Arguments:
        namespace: argparse.Namespace - Argument map of command line inputs
    Returns toplevel exit code.
    '''
    responses = dict()
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        for spec in namespace.bpmn_spec:
            with open(spec, 'rb') as spec_file_obj:
                postprocessed_xml = process_specification(spec_file_obj)
                responses[spec] = flowd.ApplyWorkflow(
                    flow_pb2.ApplyRequest(
                        bpmn_xml=postprocessed_xml,
                        stopped=namespace.stopped
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
