import argparse
import json
import logging
import os
import xmltodict
import yaml

from flowlib import flow_pb2
from flowlib import bpmn_util
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


def process_specification(spec_file):
    '''process_specification(spec_file)
    Given a BPMN specification (this can either be a file or string), perform
    rudimentary validation and cleanup of the document.  Returns a string with
    the resulting XML.
    '''
    spec = xmltodict.parse(spec_file)
    definition = spec['bpmn:definitions']
    definition_child_count = len([key for key in definition if key[0] != '@'])
    assert definition_child_count == 2, \
        f'Unexpected child count (got {definition_child_count}, not 2).'
    '''
    Check for user tasks, and if found, check for form specification files and
    import them inline.
    '''
    process = definition['bpmn:process']
    if process and 'bpmn:userTask' in process.keys():
        # if there is one userTask element, then an OrderedDict is returned by
        # process['bpmn:userTask'], otherwise it is a list of OrderedDict.
        tasks = process['bpmn:userTask']
        if not isinstance(tasks,list):
            tasks = [tasks]
        for task in tasks:
            for annot,text in bpmn_util.get_annotations(process, task['@id']):
                if 'rexflow' in text and 'fields' in text['rexflow'] and 'file' in text['rexflow']['fields']:
                    ''' Load the field description JSON from the provided file. If the file name
                    starts with anything other than '/', then assume the file is in the same folder
                    as the source BPMN file.'''
                    fspec = text['rexflow']['fields']['file']
                    if not fspec.startswith('/'):
                        fspec = '/'.join([os.path.dirname(spec_file.name),fspec])
                    try:
                        with open(fspec, 'r') as fd:
                            logging.info(f'Loading field descriptions from {fspec}')
                            data = fd.read().replace('\n','')
                            text['rexflow']['fields']['desc'] = json.loads(data)
                            annot['bpmn:text'] = yaml.dump(text)
                    except FileNotFoundError:
                        logging.error(f'File not found {fspec}')
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
