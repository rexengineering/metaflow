import requests

from flowlib import flow_pb2
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys


class ProbeHandlers:
    def __init__(self):
        self.healthd_host = 'healthd'
        self.healthd_port = 5050
        self.url = f'http://{self.healthd_host}:{self.healthd_port}/probe'

    def handle_single_deployment(self, deployment_id):
        return requests.get(f'{self.url}/{deployment_id}').json()

    def handle_some_deployments(self, ids):
        result = dict()
        for deployment_id in ids:
            result[deployment_id] = self.handle_single_deployment(deployment_id)
        return result

    def handle_all_deployments(self):
        return self.handle_single_deployment('all')

def handler(request):
    result = None
    handlers = ProbeHandlers()
    if request.ids:
        if len(request.ids) == 1:
            result = handlers.handle_single_deployment(request.ids[0])
        else:
            result = handlers.handle_some_deployments(request.ids)
    else:
        result = handlers.handle_all_deployments()
    
    return result
