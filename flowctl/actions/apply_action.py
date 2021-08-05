import argparse
import json
import logging
import os
import xmltodict
import yaml

from flowlib import flow_pb2
from flowlib import bpmn_util
from flowlib.bpmn_util import Bpmn
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import Literals

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

def _load_file(fspec:str) -> str:
    try:
        with open(fspec, 'r') as fd:
            data = fd.read().replace('\n','')
            return data
    except FileNotFoundError:
        logging.error(f'File not found {fspec}')
    return None

def process_specification(spec_file):
    """process_specification(spec_file)
    Given a BPMN specification (this can either be a file or string), perform
    rudimentary validation and cleanup of the document.  Returns a string with
    the resulting XML.
    """
    spec = xmltodict.parse(spec_file)
    definition = spec[Bpmn.definitions]
    definition_child_count = len([key for key in definition if key[0] != '@'])
    assert definition_child_count == 2, \
        f'Unexpected child count (got {definition_child_count}, not 2).'
    """
    Check for user tasks, and if found, check for form specification files and
    import them inline.
    """
    process = definition[Bpmn.process]
    if process and Bpmn.user_task in process.keys():
        # if there is one userTask element, then an OrderedDict is returned by
        # process['bpmn:userTask'], otherwise it is a list of OrderedDict.
        for task in bpmn_util.iter_xmldict_for_key(process, Bpmn.user_task):
            for annot,text in bpmn_util.get_annotations(process, task['@id']):
                try:
                    """ Load the field description JSON from the provided file. If the file name
                    starts with anything other than '/', then assume the file is in the same folder
                    as the source BPMN file."""
                    fspec = text['rexflow']['fields']['file']
                    if not fspec.startswith('/'):
                        fspec = '/'.join([os.path.dirname(spec_file.name),fspec])
                    logging.info(f'Loading field descriptions from {fspec}')
                    data = _load_file(fspec)
                    if data is not None:
                        text['rexflow']['fields']['desc'] = json.loads(data)
                        annot[Bpmn.text] = yaml.dump(text)
                except KeyError:
                    pass

        # since user tasks exist, we need to check if salesforce is in play. If so, we
        # need a salesforce profile
        for annot in bpmn_util.iter_xmldict_for_key(process, Bpmn.text_annotation):
            if annot[Bpmn.text].startswith(Literals.GLOBAL_PROPERTIES_KEY):
                text = yaml.safe_load(annot[Bpmn.text].replace('\xa0', ''))
                hive = text[Literals.GLOBAL_PROPERTIES_KEY]
                logging.info(f'\n\n{hive}\n')
                if Literals.SALESFORCE in hive and hive[Literals.SALESFORCE].keys() >= {'enabled','file'} and hive[Literals.SALESFORCE]['enabled']:
                    fspec = hive[Literals.SALESFORCE]['file']
                    if not fspec.startswith('/'):
                        fspec = '/'.join([os.path.dirname(spec_file.name),fspec])
                    logging.info(f'Loading salesforce profile from {fspec}')
                    data = _load_file(fspec)
                    if data is not None:
                        sf_info = json.loads(data)
                        hive[Literals.SALESFORCE].update(sf_info)
                        annot[Bpmn.text] = yaml.dump(text)
                break

    return xmltodict.unparse(spec)

def apply_action(namespace: argparse.Namespace, *args, **kws):
    """apply_action(namespace)
    Arguments:
        namespace: argparse.Namespace - Argument map of command line inputs
    Returns toplevel exit code.
    """
    responses = dict()
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        for spec in namespace.bpmn_spec:
            with open(spec, 'rb') as spec_file_obj:
                postprocessed_xml = process_specification(spec_file_obj)
                logging.info(postprocessed_xml)
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
