import json
import os
import re
import threading
import typing
from typing import Dict, List, NoReturn, Tuple

from etcd3.events import DeleteEvent, PutEvent
from flowlib import flow_pb2, etcd_utils
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys

flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
flowd_port = os.environ.get('FLOWD_PORT', 9001)
if ':' in flowd_port:
    # inside k8s, FLOWD_PORT has format xxx://xx.xx.xx.xx:xxxx
    # extract the IP and PORT using regex magic
    x = re.search(r'.+://([\d\.]+):(\d+)', flowd_port)
    flowd_host = x.group(1)
    flowd_port = x.group(2)

class Workflow:
    def __init__(self, did : str):
        self.did = did
        self.tasks = {}
        self.etcd = etcd_utils.get_etcd()
        self.running = False

        self.refresh_instances()
        tasks = etcd_utils.get_next_level(WorkflowKeys.probe_key(self.did))
        for tid in tasks:
            self.tasks[tid] = WorkflowTask(did,tid)

    def start(self):
        self.timer = threading.Timer(30, self.watch_instances)
        self.running = True
        self.timer.start()

    def stop(self):
        if self.running:
            self.timer.cancel()
        self.running = False

    def is_running(self):
        return self.running

    def refresh_instances(self):
        self.instances = set(
            metadata.key.decode('utf-8').split('/')[3]
            for _, metadata in self.etcd.get_prefix(WorkflowInstanceKeys.key_of(self.did), keys_only = True)
        )

    def watch_instances(self):
        watch_iter, self.cancel_watch = self.etcd.watch_prefix(WorkflowInstanceKeys.ROOT)
        for event in watch_iter:
            self.refresh_instances()

class WorkflowTask:
    def __init__(self, did:str, tid:str):
        self.did = did
        self.tid = tid
        self.fields = []
        etcd = etcd_utils.get_etcd()
        fields = etcd.get(WorkflowKeys.field_key(self.did,tid))[0]
        if fields:
            self.fields = json.loads(fields.decode('utf-8'))

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

def flowd_ps_deployment(dids : List[str] = []) -> Tuple[str,str]:
    return flowd_ps(flow_pb2.RequestKind.DEPLOYMENT, dids)

def flowd_ps_instance(iids : List[str] = []) -> Tuple[str,str]:
    return flowd_ps(flow_pb2.RequestKind.INSTANCE, iids)

def flowd_ps_deployment_instances(dids : List[str] = []) -> Tuple[str,str]:
    '''
    return instances and tasks for a given did
    '''
    pass

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    message, data = flowd_ps(flow_pb2.RequestKind.DEPLOYMENT)
    if message == 'Ok':
        info = json.loads(data)
    data = flowd_run_workflow_instance("conditional-b4e83f41")
    print(data)
    x = Workflow("conditional-b4e83f41")
        

