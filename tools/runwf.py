import json
import os
import re
import typing
from typing import Dict, List, Tuple

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection

flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
flowd_port = os.environ.get('FLOWD_PORT', 9001)
if ':' in flowd_port:
    # inside k8s, FLOWD_PORT has format xxx://xx.xx.xx.xx:xxxx
    # extract the IP and PORT using regex magic
    x = re.search(r'.+://([\d\.]+):(\d+)', flowd_port)
    flowd_host = x.group(1)
    flowd_port = x.group(2)

def flowd_run_workflow_instance(did : str, stopped : bool = False) -> Tuple[str,str]:
    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        response = flowd.RunWorkflow(flow_pb2.RunRequest(
            workflow_id=did, args=None,
            stopped=stopped, start_event_id=None
        ))
        return (response.message, response.data)

def flowd_ps(kind : flow_pb2.RequestKind, ids : List[str] = []) -> Tuple[str,str]:
    with get_flowd_connection(flowd_host, flowd_port) as flowd:
        request = flow_pb2.PSRequest(
            kind=kind, ids=ids, include_kubernetes=False,
        )
        response = flowd.PSQuery(request)
        return (response.message, response.data)

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    message, data = flowd_ps(flow_pb2.RequestKind.DEPLOYMENT)
    if message == 'Ok':
        info = json.loads(data)
    data = flowd_run_workflow_instance("conditional-b4e83f41")
    print(data)

        

