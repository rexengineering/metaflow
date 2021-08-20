import json
import logging
import sys

import xmltodict

from flowlib import bpmn, workflow
from flowlib.bpmn_util import BPMN
from flowlib.etcd_utils import get_etcd
from flowlib.constants import States, WorkflowKeys, flow_result


def handler(request):
    '''
    Arguments:
        request: gRPC apply request object.
    Returns:
        A Python dictionary that can be serialized to a JSON object.
    '''
    logger = logging.getLogger()
    result = flow_result(0, "Ok.")
    spec = xmltodict.parse(request.bpmn_xml, encoding='utf-8')
    if logger.level < logging.INFO:
        logging.debug(f'Received following BPMN specification:\n{spec}')
    process = bpmn.BPMNProcess(spec[BPMN.definitions][BPMN.process])
    assert process.id != 'flow', 'Your process name cannot be "flow", as it is a reserved prefix.'
    workflow_obj = workflow.Workflow(process)
    result["wf_id"] = workflow_obj.id
    if len(process.tasks) <= 0:
        logging.warn('No service tasks found in BPMN specification.')
    etcd = get_etcd(is_not_none=True)

    # check that the WF hasn't already been applied, and raise an error if not.
    previous_application = etcd.get(workflow_obj.keys.proc)[0]
    assert not previous_application, "Workflow ID already exists!"

    try:
        process.to_istio(None)
    except Exception as exn:
        logging.exception(
            "Failed to compile the provided bpmn diagram:",
            exc_info=exn,
        )

        exc_info = sys.exc_info()
        msg = f"Failed to compile provided bpmn diagram: {exc_info[0]} {exc_info[1]}"
        return flow_result(-1, msg)

    etcd.put(workflow_obj.keys.proc, process.to_xml())
    if request.stopped:
        if not etcd.put_if_not_exists(workflow_obj.keys.state, States.STOPPED):
            logging.error(f'{workflow_obj.keys.state} already defined in etcd!')
    else:
        # write the fields for any user tasks
        for user_task in process.user_tasks:
            if user_task.field_desc:
                etcd.put(WorkflowKeys.field_key(process.id, user_task.id), json.dumps(user_task.field_desc))
        workflow_obj.start()
    return result
