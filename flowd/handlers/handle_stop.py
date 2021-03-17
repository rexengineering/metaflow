from flowlib import flow_pb2, workflow
from flowlib.constants import BStates, WorkflowInstanceKeys
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix


def has_running_instances(wf_obj):
    etcd = get_etcd()
    instance_prefix = f'{WorkflowInstanceKeys.key_of(wf_obj.id)}-'
    instances = get_keys_from_prefix(instance_prefix)
    for inst_key in instances:
        if inst_key.endswith('/state'):
            state = etcd.get(inst_key)[0]
            if state not in (BStates.COMPLETED, BStates.ERROR):
                return True
    return False


def handler(request: flow_pb2.StopRequest):
    result = dict()
    if request.kind == flow_pb2.DEPLOYMENT:
        for id in request.ids:
            wf_obj = workflow.Workflow.from_id(id)
            if (not request.force) and has_running_instances(wf_obj):
                result[id] = {'status': -1, 'message': 'WF has live instances.'}
                continue
            try:
                wf_obj.stop()
                result[id] = {'status': 0, 'message': 'Stopped.'}
            except Exception as exn:
                result[id] = {'status': -1, 'message': f'Error: {exn}'}
    else:
        raise NotImplementedError('Lazy developer error!')

    return result
