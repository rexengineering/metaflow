import os
import typing

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
flowd_port = os.environ.get('FLOWD_PORT', 9001)

def flowd_run(did : str, stopped : bool = False) -> str:
    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        response = flowd.RunWorkflow(flow_pb2.RunRequest(
            workflow_id=did, args=None,
            stopped=stopped, start_event_id=None
        ))
    status = response.status

def flowd_ps(kind : str, ids : list[str] = []) -> list:
    if kind == 'd':
        kind = flow_pb2.RequestKind.DEPLOYMENT
    else:
        kind = flow_pb2.RequestKind.INSTANCE

    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        request = flow_pb2.PSRequest(
            kind=kind, ids=ids, include_kubernetes=False,
        )
        response = flowd.PSQuery(request)
    
    return []

def flowd_probe():
    pass

def flowd_start():
    pass

def flowd_stop():
    pass

def flowd_update():
    pass
