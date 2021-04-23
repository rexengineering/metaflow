import asyncio
import copy
import json
import logging
import os
import re
import threading
from typing import Any, Dict, List, NoReturn, Tuple

from etcd3.events import DeleteEvent, PutEvent

from flowlib import flow_pb2, etcd_utils
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys, States
from .graphql_factory import (
    ENCRYPTED,
    ID,
    DATA,
)
from .prism_api.client import PrismApiClient

class Workflow:
    def __init__(self, did : str, tids : List[str], flowd_host : str, flowd_port : int):
        self.did = did
        self.tasks = {}
        self.etcd = etcd_utils.get_etcd()
        self.running = False
        self.flowd_host = flowd_host
        self.flowd_port = flowd_port
        self.cancel_watch = None

        tasks = tids.split(':')
        for tid in tasks:
            self.tasks[tid] = WorkflowTask(self,tid)
        logging.info(f'Workflow object initialized to process workflow {did}')

    def start(self):
        self.timer = threading.Timer(1, self.watch_instances)
        self.running = True
        self.timer.start()
        logging.info(f'{self.did} started')

    def stop(self):
        if self.running:
            self.timer.cancel()
        self.running = False
        logging.info(f'{self.did} stopped')

    def is_running(self):
        return self.running

    def watch_instances(self):
        '''
        monitor the state keys of the instances belonging to our workflow. If any of them
        disappear (delete) or change to COMPLETED or ERROR state, notify prism that the
        instance has gone away ...
        '''
        watch_iter, _ = self.etcd.watch_prefix(WorkflowInstanceKeys.key_of(self.did))
        for event in watch_iter:
            key   = event.key.decode('utf-8')
            value = event.value.decode('utf-8')
            if key.endswith('/state'):
                iid = key.split('/')[3]
                if isinstance(event, PutEvent):
                    if value in (States.COMPLETED, States.ERROR):
                        '''notify any graphql_uri that this instance is done'''
                        endpoint = self.get_instance_graphql_uri(iid)
                        if endpoint:
                            asyncio.run(self.notify_prism_iid_complete(endpoint, iid, value))
                elif isinstance(event, DeleteEvent):
                    '''
                    Delete is complicated, because we only want to presume the instance has
                    been deleted if the instance ROOT key is deleted, and not necessarilly
                    any of its children. In this case, we might get notified for every key
                    that's deleted.
                    '''
                    pass

    async def notify_prism_iid_complete(self, endpoint:str, iid:str, state:str) -> NoReturn:
        response = await PrismApiClient.complete_workflow(endpoint,iid)
        logging.info(f'Notifying {endpoint} that {iid} has completed state ({state}); response {response}')

    def create_instance(self, graphql_uri:str):
        with get_flowd_connection(self.flowd_host, self.flowd_port) as flowd:
            response = flowd.RunWorkflow(flow_pb2.RunRequest(
                workflow_id=self.did, args=None,
                stopped=False, start_event_id=None
            ))
            data = json.loads(response.data)
            if graphql_uri:
                iid = data[ID]
                self.etcd.put(WorkflowInstanceKeys.ui_server_uri_key(iid), graphql_uri)
            return data

    def get_instances(self):
        with get_flowd_connection(self.flowd_host, self.flowd_port) as flowd:
            request = flow_pb2.PSRequest(
                kind=flow_pb2.INSTANCE, ids = [], include_kubernetes=False,
            )
            response = flowd.PSQuery(request)
            data = json.loads(response.data)
            return [key for key in data.keys() if key.startswith(self.did)]

    def get_instance_graphql_uri(self, iid:str) -> str:
        uri, _ = self.etcd.get(WorkflowInstanceKeys.ui_server_uri_key(iid))
        if uri:
            uri = uri.decode('utf-8')
        return uri      # will be None or the URI

    def get_task_ids(self):
        return self.tasks.keys()

    def task(self, tid : str):
        if tid not in self.tasks.keys():
            return None
        return self.tasks[tid]


class WorkflowTask:
    def __init__(self, wf:Workflow, tid:str):
        self.wf = wf
        self.tid = tid
        self._fields = {}   # the immutable complete set of form information
        self._values = {}   # the immutable initial set of form data
        form, _ = wf.etcd.get(WorkflowKeys.field_key(wf.did,tid))
        if form:
            self._fields = self._normalize_fields(form)
            for k,v in self._fields.items():
                self._values[k] = v[DATA]

    def get_form(self,iid:str):
        '''
        Pull the task form for the given iid. If the iid record does not exist,
        create the iid form from the did form master.
        '''
        key = WorkflowInstanceKeys.task_form_key(iid,self.tid)
        form, _ = self.wf.etcd.get(key)
        if form is None:
            tid_key = WorkflowKeys.field_key(self.wf.did,self.tid)
            form, _ = self.wf.etcd.get(tid_key)
            self.wf.etcd.put(key,form)
        return list(self._normalize_fields(form).values())

    def update(self, iid:str, in_fields:list):
        # get the current fields into a dict for easy access!
        tmp = self.get_form(iid)
        flds = {}
        for f in tmp:
            flds[f[ID]] = f
        for f in in_fields:
            flds[f[ID]][DATA] = f[DATA]
        key = WorkflowInstanceKeys.task_form_key(iid,self.tid)
        val = json.dumps(list(flds.values()))
        self.wf.etcd.put(key, val)
        return flds

    def _normalize_fields(self, form:str) -> Dict[str, Any]:
        '''
        graphql provides booleans as strings, so convert them to their python equivalents.
        '''
        fields = {}
        field_list = json.loads(form.decode('utf-8'))
        for field in field_list:
            field[ENCRYPTED] = bool(field[ENCRYPTED])
            fields[field[ID]] = field
        return fields

    def fields(self, iid:str = None) -> List[Any]:
        '''
        Return the fields for this task. If iid is provided, pull
        the values for the iid and return a deep copy of the fields
        for the i.
        '''
        if iid:
            # deep copy of fields
            flds = copy.deepcopy(list(self._fields.values()))
            # pull iid values record
            vals = {}
            # replace data members in flds with iid values
            for key,val in vals.items():
                flds[key][DATA] = val
            return flds
        return self._fields.values()

    def field(self, id : str) -> Dict[str, Any]:
        if id not in self._fields.keys():
            raise ValueError(f'Field {id} does not exist in task {self.tid}')
        return self._fields[id]

if __name__ == "__main__":
    # flowd_run_workflow_instance("tde-15839350")
    # message, data = flowd_ps(flow_pb2.RequestKind.DEPLOYMENT)
    # if message == 'Ok':
    #     info = json.loads(data)
    # data = flowd_run_workflow_instance("conditional-b4e83f41")
    # print(data)
    from flowlib.constants import BStates
    import time
    did = "process-0p1yoqw-aa16211c"
    iid = 'process-0p1yoqw-aa16211c-bogus'
    x = Workflow(did, 'a:b:c', 'localhost', 9001)
    x.start()
    x.notify_prism_iid_complete("http://localhost:8000/callback", iid, BStates.COMPLETED)
    etcd = etcd_utils.get_etcd()
    keys = WorkflowInstanceKeys(iid)
    etcd.put(keys.ui_server_uri_key(iid), "http://localhost:8000/callback")
    time.sleep(5)
    etcd.put(keys.state, BStates.RUNNING)
    etcd.put(keys.state, BStates.COMPLETED)
    print('hello')

