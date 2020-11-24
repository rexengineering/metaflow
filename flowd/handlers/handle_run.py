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
        wf_instance = workflow.WorkflowInstance(wf_deployment)
        logger.info(f'Running {wf_instance.id}...')
        if not etcd.put_if_not_exists(wf_instance.keys.state, States.STARTING):
            logging.error(f'{wf_instance.keys.state} already defined in etcd!')
        etcd.put(f'{wf_instance.keys.root}/parent', wf_instance.parent.id)
        result[request.workflow_id] = wf_instance.id
        executor_obj = executor.get_executor()
        executor_obj.submit(wf_instance.start, *request.args)
    return result
