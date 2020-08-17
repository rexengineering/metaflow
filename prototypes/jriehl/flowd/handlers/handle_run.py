import logging

import requests

from flowlib import executor, workflow
from flowlib.etcd_utils import get_etcd


def handler(request):
    logger = logging.getLogger()
    result = dict()
    etcd = get_etcd(is_not_none=True)
    wf_deployment = workflow.Workflow.from_id(request.workflow_id)
    wf_instance = workflow.WorkflowInstance(wf_deployment)
    logger.info(f'Running {wf_instance.id}...')
    etcd.put(f'{wf_instance.key_prefix}/state', 'STARTING')
    result[request.workflow_id] = wf_instance.id
    executor_obj = executor.get_executor()
    executor_obj.submit(wf_instance.start, *request.args)
    return result
