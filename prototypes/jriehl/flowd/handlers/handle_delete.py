import logging

from flowlib import flow_pb2
from flowlib.etcd_utils import get_etcd, EtcdDict


def handler(request : flow_pb2.DeleteRequest):
    '''
    Arguments:
        request: gRPC delete request object.
    Returns:
        A Python dictionary that can be serialized to a JSON object.
    '''
    result = dict()
    etcd = get_etcd(is_not_none=True)
    request_kind = request.kind
    if request_kind == flow_pb2.RequestKind.DEPLOYMENT:
        for workflow_id in request.ids:
            prefix = f'/rexflow/workflows/{workflow_id}'
            workflow = EtcdDict.from_root(prefix)
            if len(workflow) <= 0:
                message = f'Workflow deployment {workflow_id} was not found.'
                logging.warn(message)
                result[workflow_id] = dict(result=-1, message=message)
                continue
            workflow_state = workflow['state']
            print(workflow_state)
            if workflow_state != b'STOPPED':
                message = f'Workflow deployment {workflow_id} is not in the STOPPED state.'
                logging.warn(message)
                result[workflow_id] = dict(result=-2, message=message)
            elif etcd.delete_prefix(prefix):
                message = f'Successfully deleted {workflow_id}.'
                logging.info(message)
                result[workflow_id] = dict(result=0, message=message)
            else:
                message = f'Failed to fully delete {workflow_id} in the backing store.'
                logging.error(message)
                result[workflow_id] = dict(result=-3, message=message)
    elif request_kind == flow_pb2.RequestKind.INSTANCE:
        for instance_id in request.ids:
            prefix = f'/rexflow/runs/{instance_id}'
            keys = [metadata.key.decode('utf-8') for _, metadata in etcd.get_prefix(prefix, keys_only=True)]
            if len(keys) <= 0:
                message = f'Workflow instance {instance_id} was not found.'
                logging.warn(message)
                result[instance_id] = dict(result=-1, message=message)
                continue
            # FIXME: Do something here.
    else:
        raise ValueError(f'Unknown request kind ({request_kind})!')
    return result
