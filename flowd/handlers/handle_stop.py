from flowlib import flow_pb2, workflow
from flowlib.constants import BStates, WorkflowInstanceKeys, flow_result
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix
from flowlib.ingress_utils import get_host_dict

def has_running_instances(wf_obj, etcd=None):
    etcd = etcd or get_etcd()
    instance_prefix = f'{WorkflowInstanceKeys.key_of(wf_obj.id)}-'
    instances = get_keys_from_prefix(instance_prefix)
    for inst_key in instances:
        if inst_key.endswith('/state'):
            state = etcd.get(inst_key)[0]
            if state not in (BStates.COMPLETED, BStates.ERROR):
                return True
    return False


def handler(request: flow_pb2.StopRequest):
    etcd = get_etcd()
    result = dict()
    if request.kind == flow_pb2.DEPLOYMENT:
        for id in request.ids:
            wf_obj = workflow.Workflow.from_id(id)
            # no matter what, must *successfully* delete ingress before deleting wf.
            current_host_dict = get_host_dict(id)
            if bool(current_host_dict) and not request.force:
                result[id] = flow_result(
                    -1,
                    f'WF {wf_obj.id} still has exposed Ingress.'
                )
                continue
            if (not request.force) and has_running_instances(wf_obj, etcd=etcd):
                result[id] = {'status': -1, 'message': 'WF has running instances.'}
                continue
            try:
                wf_obj.stop()
                result[id] = {'status': 0, 'message': 'Stopped.'}
            except Exception as exn:
                result[id] = {'status': -1, 'message': f'Error: {exn}'}
    else:
        raise NotImplementedError('Lazy developer error!')

    return result
