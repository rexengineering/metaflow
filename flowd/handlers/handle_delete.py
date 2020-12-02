import logging

from flowlib import flow_pb2
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix, EtcdDict
from flowlib.constants import BStates, WorkflowKeys, WorkflowInstanceKeys
from flowlib.workflow import Workflow


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
            prefix = WorkflowKeys.key_of(workflow_id)
            workflow = EtcdDict.from_root(prefix)
            if len(workflow) <= 0:
                message = f'Workflow deployment {workflow_id} was not found.'
                logging.warn(message)
                result[workflow_id] = dict(result=-1, message=message)
                continue
            workflow_state = workflow['state']
            if workflow_state not in {BStates.ERROR, BStates.STOPPED}:
                message = f'Workflow deployment {workflow_id} is not in the ERROR or STOPPED state.'
                logging.warn(message)
                result[workflow_id] = dict(result=-2, message=message)
            # FIXME: Double check we're in an acceptable state.  Also, tear down
            # the deployment in the container orchestrator, and ensure the tear
            # down completes.
            # FIXME: Do we need some sort of DELETING state, or other lock
            # on the deployment?
            else:
                wf = Workflow.from_id(workflow_id)
                wf.remove()
                # FIXME: Should deleting a workflow also delete all workflow
                # instance history as well?
                if etcd.delete_prefix(prefix):
                    message = f'Successfully deleted {workflow_id}.'
                    logging.info(message)
                    result[workflow_id] = dict(result=0, message=message)
                else:
                    message = f'Failed to fully remove {workflow_id} from the backing store.'
                    logging.error(message)
                    result[workflow_id] = dict(result=-3, message=message)
    elif request_kind == flow_pb2.RequestKind.INSTANCE:
        for instance_id in request.ids:
            prefix = WorkflowInstanceKeys.key_of(instance_id)
            keys = get_keys_from_prefix(prefix)
            if len(keys) <= 0:
                message = f'Workflow instance {instance_id} was not found.'
                logging.warn(message)
                result[instance_id] = dict(result=-1, message=message)
                continue
            state_key = WorkflowInstanceKeys.state_path(instance_id)
            instance_state = etcd.get(state_key)[0]
            good_states = {BStates.STOPPED, BStates.ERROR, BStates.COMPLETED}
            logging.debug(instance_state)
            if instance_state not in good_states:
                message = f'Workflow instance {instance_id} is not in the '\
                           'COMPLETED, ERROR, or STOPPED state.'
                logging.warn(message)
                result[instance_id] = dict(result=-2, message=message)
            elif etcd.delete_prefix(prefix):
                message = f'Successfully deleted {instance_id}.'
                logging.info(message)
                result[instance_id] = dict(result=0, message=message)
            else:
                message = f'Failed to fully remove {instance_id} from the backing store.'
                logging.error(message)
                result[instance_id] = dict(result=-3, message=message)
    else:
        raise ValueError(f'Unknown delete request kind ({request_kind})!')
    return result
