import json
import os
import typing

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
flowd_port = os.environ.get('FLOWD_PORT', 9001)

def flowd_run_workflow_instance(did : str, stopped : bool = False) -> str:
    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        response = flowd.RunWorkflow(flow_pb2.RunRequest(
            workflow_id=did, args=None,
            stopped=stopped, start_event_id=None
        ))
        print(response)

def flowd_ps(kind : flow_pb2.RequestKind, ids : typing.List[str] = []) -> typing.Tuple[str,str]:
    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        request = flow_pb2.PSRequest(
            kind=kind, ids=ids, include_kubernetes=False,
        )
        response = flowd.PSQuery(request)
        return (response.message, response.data)

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    message, data = flowd_ps(flow_pb2.RequestKind.INSTANCE)
    if message == 'Ok':
        info = json.loads(data)
        

