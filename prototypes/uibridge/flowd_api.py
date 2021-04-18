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
    def __init__(self, did : str, tids : str, flowd_host : str, flowd_port : int):
        self.did = did
        self.tasks = {}
        self.etcd = etcd_utils.get_etcd()
        self.running = False
        self.flowd_host = flowd_host
        self.flowd_port = flowd_port

        self.refresh_instances()
        tasks = tids.split(':')
        for tid in tasks:
            self.tasks[tid] = WorkflowTask(self,tid)
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

    def task(self, tid : str):
        if tid not in self.tasks.keys():
            return None
        return self.tasks[tid]


class WorkflowTask:
    def __init__(self, wf:Workflow, tid:str):
        self.wf = wf
        self.tid = tid
        self._fields = {}
        form,_ = wf.etcd.get(WorkflowKeys.field_key(wf.did,tid))
        if form:
            self._fields = self.normalize_fields(form)

    def pull(self,iid:str):
        '''
        Pull the task form for the given iid. If the iid record does not exist,
        create the iid form from the did form master.
        '''
        key = WorkflowInstanceKeys.task_form_key(iid,self.tid)
        print(f'Trying to pull form data for {key}', flush=True)
        form, _ = self.wf.etcd.get(key)
        print(f'Result for {key} is {form}', flush=True)
        if form is None:
            tid_key = WorkflowKeys.field_key(self.wf.did,self.tid)
            print(f'Trying to pull form data from {tid_key}', flush=True)
            form, _ = self.wf.etcd.get(tid_key)
            print(f'Result for {tid_key} is {form}', flush=True)
            self.wf.etcd.put(key,form)
        return self.normalize_fields(form).values()

    def normalize_fields(self, form:str) -> Dict[str,typing.Any]:
        fields = {}
        field_list = json.loads(form.decode('utf-8'))
        for field in field_list:
            field['encrypted'] = bool(field['encrypted'])
            fields[field['id']] = field
        print(fields)
        return fields

    def fields(self) -> List[any]:
        return self._fields.values()

    def field(self, id : str) -> Dict[str,any]:
        if id not in self._fields.keys():
            raise ValueError(f'Field {id} does not exist in task {self.tid}')
        return self._fields[id]

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    message, data = flowd_ps(flow_pb2.RequestKind.DEPLOYMENT)
    if message == 'Ok':
        info = json.loads(data)
    data = flowd_run_workflow_instance("conditional-b4e83f41")
    print(data)
    x = Workflow("conditional-b4e83f41")
