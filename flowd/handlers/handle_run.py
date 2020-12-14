import logging

import requests

from flowlib import executor, workflow
from flowlib.etcd_utils import get_etcd
from flowlib.constants import States, BStates

def handler(request):
    logger = logging.getLogger()
    result = dict()
    etcd = get_etcd(is_not_none=True)
    wf_deployment = workflow.Workflow.from_id(request.workflow_id)

    # workflow must be in RUNNING state to run an instance of it.
    state = etcd.get(wf_deployment.keys.state)[0]
    if state != BStates.RUNNING:
        message = f'Deployment {wf_deployment.id} is not RUNNING. {state}'
        logging.warn(message)
        result[request.workflow_id] = dict(result=-1, message=message)
    else:
        instance = workflow.WorkflowInstance(parent=wf_deployment)
        result = instance.start()
    return result
