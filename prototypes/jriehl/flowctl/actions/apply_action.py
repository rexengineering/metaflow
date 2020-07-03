import argparse
import logging

from bs4 import BeautifulSoup

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

__help__ = 'apply sufficiently annotated BPMN file(s)'

def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('bpmn_spec', nargs='+', help='sufficiently annotated BPMN file(s)')
    return parser

def process_specification(specification):
    spec_soup = BeautifulSoup(specification, 'lxml')
    spec_body_children = tuple(spec_soup.body.children)
    spec_body_child_count = len(spec_body_children)
    assert len(spec_body_children) == 2, \
        f'Unexpected child count ({spec_body_child_count} != 2).'
    spec_defns = spec_body_children[0]
    return str(spec_defns)


def apply_action(namespace : argparse.Namespace, *args, **kws):
    '''apply_action(namespace)
    Arguments:
        namespace : argparse.Namespace - Argument map of command line inputs
    Returns toplevel exit code.
    '''
    responses = dict()
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        for spec in namespace.bpmn_spec:
            with open(spec) as spec_file_obj:
                postprocessed_xml = process_specification(spec_file_obj)
                responses[spec] = flowd.ApplyWorkflow(
                        flow_pb2.ApplyRequest(bpmn_xml=postprocessed_xml)
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
    return status
