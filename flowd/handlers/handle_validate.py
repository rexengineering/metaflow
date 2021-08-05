from io import StringIO
import json
import logging
import sys

import xmltodict

from flowlib import bpmn, workflow
from flowlib.bpmn_util import Bpmn
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

    try:
        spec = xmltodict.parse(request.bpmn_xml, encoding='utf-8')
        if logger.level < logging.INFO:
            logging.debug(f'VALIDATE: Received following BPMN specification:\n{spec}')
        process = bpmn.BPMNProcess(spec[Bpmn.definitions][Bpmn.process])
        assert process.id != 'flow', 'Your process name cannot be "flow", as it is a reserved prefix.'
        workflow_obj = workflow.Workflow(process)
        result["wf_id"] = workflow_obj.id
        if len(process.tasks) <= 0:
            logging.warn('No service tasks found in BPMN specification.')
        stream = StringIO()
        process.to_istio(stream)
    except Exception as exn:
        logging.exception(
            "Failed to compile the provided bpmn diagram:",
            exc_info=exn,
        )

        exc_info = sys.exc_info()
        msg = f"Failed to compile provided bpmn diagram: {exc_info[0]} {exc_info[1]}"
        return flow_result(-1, msg)

    if request.include_kubernetes:
        result["k8s_specs"] = stream.getvalue()
        result["The Force"] = "with us."
    return result
