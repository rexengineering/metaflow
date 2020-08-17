import logging

from flowlib import flow_pb2
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix, EtcdDict


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
            if workflow_state not in {b'ERROR', b'STOPPED'}:
                message = f'Workflow deployment {workflow_id} is not in the ERROR or STOPPED state.'
                logging.warn(message)
                result[workflow_id] = dict(result=-2, message=message)
            # FIXME: Double check we're in an acceptable state.  Also, tear down
            # the deployment in the container orchestrator, and ensure the tear
            # down completes.
            # FIXME: Do we need some sort of DELETING state, or other lock
            # on the deployment?
            elif etcd.delete_prefix(prefix):
                message = f'Successfully deleted {workflow_id}.'
                logging.info(message)
                result[workflow_id] = dict(result=0, message=message)
            else:
                message = f'Failed to fully remove {workflow_id} from the backing store.'
                logging.error(message)
                result[workflow_id] = dict(result=-3, message=message)
    elif request_kind == flow_pb2.RequestKind.INSTANCE:
        for instance_id in request.ids:
            prefix = f'/rexflow/instances/{instance_id}'
            keys = get_keys_from_prefix(prefix)
            if len(keys) <= 0:
                message = f'Workflow instance {instance_id} was not found.'
                logging.warn(message)
                result[instance_id] = dict(result=-1, message=message)
                continue
            # FIXME: Do something here.
            raise NotImplementedError('Laxy developer error!') # Does something!
    else:
        raise ValueError(f'Unknown delete request kind ({request_kind})!')
    return result
