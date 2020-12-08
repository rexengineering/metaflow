from flowlib import (
    flow_pb2,
    workflow,
    constants,
    etcd_utils,
    workflow,
)

def handler(request : flow_pb2.StartRequest):
    result = dict()
    if request.kind == flow_pb2.DEPLOYMENT:
        for id in request.ids:
            wf_obj = workflow.Workflow.from_id(id)
            try:
                wf_obj.start()
                result[id] = {'status':0, 'message':'Started.'}
            except Exception as exn:
                result[id] = {'status':-1, 'message':f'Error: {exn}'}
    else:
        for id in request.ids:
            etcd = etcd_utils.get_etcd()

            # First check to see that the thing is in the `STOPPED` state.
            state_key = constants.WorkflowInstanceKeys.state_key(id)
            state = etcd.get(state_key)[0]
            assert state == constants.BStates.STOPPED, "Can only start instances in STOPPED state"

            # We need to go from WF Instance ID to WF Id in order to construct the
            # Workflow Object (which is necessary to create the Workflow Instance Object).
            # Recall that Gary has edited the code such that the Instance Id contains the
            # Workflow Id. We use that functionality here.
            wf_id = constants.split_key(id)[0]

            # now we can get the Workflow Object
            wf_obj = workflow.Workflow.from_id(wf_id)
            wf_instance_obj = workflow.WorkflowInstance(wf_obj, id=id)

            result[id] = wf_instance_obj.retry()

    return result
