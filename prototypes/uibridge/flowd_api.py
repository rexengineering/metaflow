import json
import logging
import os
import re
import threading
import typing
from typing import Dict, List, NoReturn, Tuple

from etcd3.events import DeleteEvent, PutEvent
from flowlib import flow_pb2, etcd_utils
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys

class Workflow:
    def __init__(self, did : str, flowd_host : str, flowd_port : int):
        self.did = did
        self.tasks = {}
        self.etcd = etcd_utils.get_etcd()
        self.running = False
        self.flowd_host = flowd_host
        self.flowd_port = flowd_port

        self.refresh_instances()
        tasks = etcd_utils.get_next_level(WorkflowKeys.probe_key(self.did))
        for tid in tasks:
            self.tasks[tid] = WorkflowTask(did,tid)
        logging.info(f'Workflow object initialized to process workflow {did}')

    def start(self):
        self.timer = threading.Timer(30, self.watch_instances)
        self.running = True
        self.timer.start()
        logging.info(f'{self.did} started')

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
        for _ in watch_iter:
            self.refresh_instances()

    def create_instance(self):
        with get_flowd_connection(self.flowd_host, self.flowd_port) as flowd:
            response = flowd.RunWorkflow(flow_pb2.RunRequest(
                workflow_id=self.did, args=None,
                stopped=False, start_event_id=None
            ))
            return response

class WorkflowTask:
    def __init__(self, did:str, tid:str):
        self.did = did
        self.tid = tid
        self.fields = []
        etcd = etcd_utils.get_etcd()
        fields = etcd.get(WorkflowKeys.field_key(self.did,tid))[0]
        if fields:
            self.fields = json.loads(fields.decode('utf-8'))

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    message, data = flowd_ps(flow_pb2.RequestKind.DEPLOYMENT)
    if message == 'Ok':
        info = json.loads(data)
    data = flowd_run_workflow_instance("conditional-b4e83f41")
    print(data)
    x = Workflow("conditional-b4e83f41")
        



def flowd_ps_deployments(dids : List[str] = []) -> Tuple[str,str]:
    return flowd_ps(flow_pb2.RequestKind.DEPLOYMENT, dids)

def flowd_ps_instances(iids : List[str] = []) -> Tuple[str,str]:
    return flowd_ps(flow_pb2.RequestKind.INSTANCE, iids)

def flowd_ps_instances_for_deployment(did : str) -> Dict:
    pass
    
def flowd_probe():
    pass

def flowd_start():
    pass

def flowd_stop():
    pass

def flowd_update():
    pass
