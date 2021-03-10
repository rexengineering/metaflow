import logging

import xmltodict

from flowlib import bpmn, workflow
from flowlib.etcd_utils import get_etcd
from flowlib.constants import States


def handler(request):
    '''
    Arguments:
        request: gRPC apply request object.
    Returns:
        A Python dictionary that can be serialized to a JSON object.
    '''
    logger = logging.getLogger()
    result = dict()
    spec = xmltodict.parse(request.bpmn_xml, encoding='utf-8')
    if logger.level < logging.INFO:
        logging.debug(f'Received following BPMN specification:\n{spec}')
    process = bpmn.BPMNProcess(spec['bpmn:definitions']['bpmn:process'])
    assert process.id != 'flow', 'Your process name cannot be "flow", as it is a reserved prefix.'
    workflow_obj = workflow.Workflow(process)
    result["wf_id"] = workflow_obj.id
    if len(process.tasks) <= 0:
        logging.warn('No service tasks found in BPMN specification.')
    etcd = get_etcd(is_not_none=True)

    # check that the WF hasn't already been applied, and raise an error if not.
    previous_application = etcd.get(workflow_obj.keys.proc)[0]
    assert not previous_application, "Workflow ID already exists!"

    etcd.put(workflow_obj.keys.proc, process.to_xml())
    if request.stopped:
        if not etcd.put_if_not_exists(workflow_obj.state_key, States.STOPPED):
            logging.error(f'{workflow_obj.state_key} already defined in etcd!')
    else:
        workflow_obj.start()
    return result
