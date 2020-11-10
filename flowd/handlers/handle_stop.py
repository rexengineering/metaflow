import logging
from flowlib import flow_pb2, workflow

def handler(request : flow_pb2.StopRequest):
    result = dict()
    if request.kind == flow_pb2.DEPLOYMENT:
        for id in request.ids:
            wf_obj = workflow.Workflow.from_id(id)
            try:
                wf_obj.stop()
                result[id] = {'status':0, 'message':'Stopped.'}
            except Exception as exn:
                result[id] = {'status':-1, 'message':f'Error: {exn}'}
    else:
        raise NotImplementedError('Lazy developer error!')
    
    return result
