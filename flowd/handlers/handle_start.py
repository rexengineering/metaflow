from flowlib import flow_pb2, workflow


def handler(request: flow_pb2.StartRequest):
    result = dict()
    if request.kind == flow_pb2.DEPLOYMENT:
        for id in request.ids:
            wf_obj = workflow.Workflow.from_id(id)
            try:
                wf_obj.start()
                result[id] = {'status': 0, 'message': 'Started.'}
            except Exception as exn:
                result[id] = {'status': -1, 'message': f'Error: {exn}'}
    else:
        raise NotImplementedError('Lazy developer error!')
    return result
