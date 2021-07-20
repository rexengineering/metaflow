import copy
import logging
import json
from flowlib import workflow
from flowlib.etcd_utils import get_etcd, EtcdDict
from flowlib.constants import BStates

def handler(request):
    workflow_id = request.workflow_id

    # for developer convenience, attempt to find a workflow ID based on a simple substring match;
    # if the match is ambiguous (more than one), silently fall back to exact matching
    wf_keys = []

    for wf_key, wf_data in EtcdDict.from_root(f'/rexflow/workflows').items():
        if workflow_id in wf_key:
            wf_keys.append(wf_key)

    if len(wf_keys) == 1:
        workflow_id = wf_keys[0]

    wf_deployment = workflow.Workflow.from_id(workflow_id)
    result = dict()
    etcd = get_etcd(is_not_none=True)

    # workflow must be in RUNNING state to run an instance of it.

    state = etcd.get(wf_deployment.keys.state)[0]
    if state != BStates.RUNNING:
        message = f'Deployment {wf_deployment.id} is not RUNNING. {state}'
        logging.warn(message)
        result[workflow_id] = dict(result=-1, message=message)
    else:
        instance = workflow.WorkflowInstance(parent=wf_deployment)
        result = instance.start(start_event_id=request.start_event_id)
        if 'id' in result:
            iid = result['id']
            instance = workflow.WorkflowInstance(parent=wf_deployment, id=iid)
            # pull default metadata from BPMN deployment
            instance_meta = copy.deepcopy(instance.parent.properties.user_metadata)
            # pull any metadata provided with the RUN request
            run_metadata = {obj.key: obj.value for obj in request.metadata}
            if run_metadata:
                # overlay the RUN metadata over the 'default' metadata
                instance_meta.update(run_metadata)
            logging.info(f'metadata {instance_meta} {type(instance_meta).__name__}')
            etcd.put(instance.keys.metadata, json.dumps(instance_meta).encode())
    return result
