import asyncio
import copy
import functools
import json
import logging
import os
import re
import requests
import threading
import uuid
from typing import Any, Dict, List, NoReturn, Tuple

from etcd3.events import DeleteEvent, PutEvent

from flowlib import flow_pb2, etcd_utils, executor
from flowlib.etcd_utils import locked_call
from flowlib.flowpost import FlowPost, FlowPostResult, FlowPostStatus
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys, States, TEST_MODE_URI, Headers
from .graphql_wrappers import (
    DataType,
    is_ignored_data_type,
    ENCRYPTED,
    EVAL,
    DATA_ID,
    DEFAULT,
    DATA,
    ID,
    KEY,
    META_DATA,
    TEXT,
    TYPE,
    UNKNOWN,
    VALUE,
)
from .prism_api.client import PrismApiClient

class Workflow:
    # forward decl for Workflow
    pass

class PostRequest:
    def __init__(self, parent:Workflow, next_task:dict, next_headers:dict, data:dict):
        self._guid         = uuid.uuid4().hex
        self._parent       = parent
        self._next_task    = next_task
        self._next_headers = next_headers
        self._data         = data
        self._svc_response = None

    def __call__(self):
        try:
            call = requests.post if self._next_task['method'] == 'POST' else requests.get
            self._svc_response = call(self._next_task['k8s_url'], headers=self._next_headers, json=self._data)
            self._svc_response.raise_for_status()
            # try:
            #     self.save_traceid(svc_response.headers, iid)
            # except Exception as exn:
            #     logging.exception("Failed to save trace id on WF Instance", exc_info=exn)
            # self._shadow_to_kafka(data, next_headers)
            logging.info(self._svc_response)
        except Exception as exn:
            logging.exception(
                f"failed making a call to {self._next_task['k8s_url']} on wf {iid}\nheaders:{self._next_headers}", #\ndata:{self._data}",
                exc_info=exn,
            )
        self._parent.set_post_response(self._guid, self._svc_response)

    @property
    def guid(self):
        return self._guid

    @property
    def response(self):
        return self._svc_response

class Workflow:
    def __init__(self, did : str, tids : List[str], bridge_cfg : dict, flowd_host : str, flowd_port : int):
        self.did = did
        self.bridge_cfg = bridge_cfg
        self.tasks = {}
        self.etcd = etcd_utils.get_etcd()
        self.running = False
        self.flowd_host = flowd_host
        self.flowd_port = flowd_port
        self.cancel_watch = None
        self.instance_headers = {}
        self.instance_data = {}
        self.reponses = {}

        for tid in tids:
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

    def register_instance_header(self, iid:str, header:str):
        if iid not in self.instance_headers.keys():
            self.instance_headers[iid] = []
        self.instance_headers[iid].append(header)
        logging.info(f'{iid} header {header}')

    def set_instance_data(self, iid:str, data):
        self.instance_data[iid] = data

    def get_instance_data(self, iid:str):
        if iid in self.instance_data:
            return self.instance_data[iid]
        return None

    def get_status(self) -> str:
        return self._get_etcd_value(WorkflowKeys.state_key(self.did))

    def watch_instances(self):
        """
        monitor the state keys of the instances belonging to our workflow. If any of them
        disappear (delete) or change to COMPLETED or ERROR state, notify prism that the
        instance has gone away ...
        """
        watch_iter, _ = self.etcd.watch_prefix(WorkflowInstanceKeys.key_of(self.did))
        for event in watch_iter:
            key   = event.key.decode('utf-8')
            value = event.value.decode('utf-8')
            if key.endswith('/state'):
                iid = key.split('/')[3]
                if isinstance(event, PutEvent):
                    if value in (States.COMPLETED, States.ERROR):
                        """notify any graphql_uri that this instance is done"""
                        prism_endpoint = self.get_instance_graphql_uri(iid)
                        if prism_endpoint and prism_endpoint != TEST_MODE_URI:
                            asyncio.run(self.notify_prism_iid_complete(prism_endpoint, iid, value))
                elif isinstance(event, DeleteEvent):
                    """
                    Delete is complicated, because we only want to presume the instance has
                    been deleted if the instance ROOT key is deleted, and not necessarilly
                    any of its children. In this case, we might get notified for every key
                    that's deleted.
                    """
                    pass

    async def notify_prism_iid_complete(self, endpoint:str, iid:str, state:str) -> NoReturn:
        response = await PrismApiClient.complete_workflow(endpoint,iid)
        logging.info(f'Notifying {endpoint} that {iid} has completed state ({state}); response {response}')

    def create_instance(self, did:str, graphql_uri:str, meta:list):
        """
        Run a workflow instance. If did is none, run the workflow for this UI-BRIDGE,
        else resolve the DID to a workflow deployment fia the workflow map, and ask
        flowd to run that workflow instance.
        """
        wf_id = None
        if did is not None:
            # pull the current workflow map from flowd
            wf_map = self.get_wf_map()
            logging.info(f'Searching workflow map for {did}')
            for k,v in wf_map.items():
                # the did might be the process id from the BPMN, or the
                # deployment id from k8s, so account for both
                # v is a list of workflow info, so if > 1 then we take the
                # first one.
                wf_info = v[0]
                logging.info(f'-- Trying {k} {wf_info[ID]}')
                if did.upper() in [k.upper(), wf_info[ID].upper()]:    # ignore case
                    wf_id = wf_info[ID]
                    logging.info(f'Found {wf_id}!')
                    break
            if wf_id is None:
                raise ValueError(f'Workflow {did} is not available')
        else:
            wf_id = self.did

        md = [
            flow_pb2.StringPair(key=m[KEY], value=m[VALUE])
            for m in meta
        ]
        print(md)
        with get_flowd_connection(self.flowd_host, self.flowd_port) as flowd:
            response = flowd.RunWorkflow(flow_pb2.RunRequest(
                workflow_id=wf_id, args=None,
                stopped=False, start_event_id=None,
                metadata=md
            ))
            data = json.loads(response.data)
            if graphql_uri:
                iid = data[ID]
                self._put_etcd_value(WorkflowInstanceKeys.ui_server_uri_key(iid), graphql_uri)
            return data

    def cancel_instance(self, iid:str):
        if iid in self.get_instances():
            status = self.get_instance_status(iid)
            if status not in ['STOPPED','ERROR']:
                poster = FlowPost(iid, None, '{}')
                response = poster.cancel_instance()
                logging.info(response)
                status = self.get_instance_status(iid)
            return status
        raise ValueError(f'{iid} is not a known instance')

    def get_instances(self, meta:dict = None) -> list:
        metadata = None
        if meta is not None:
            metadata = [
                flow_pb2.StringPair(key=k, value=v)
                for k,v in meta.items()
            ]
        with get_flowd_connection(self.flowd_host, self.flowd_port) as flowd:
            request = flow_pb2.PSRequest(
                kind=flow_pb2.INSTANCE, ids = [], include_kubernetes=False, metadata=metadata
            )
            response = flowd.PSQuery(request)
            logging.info(f'get_instances req:{request} res:{response}')
            data = json.loads(response.data)
            return [key for key in data.keys() if key.startswith(self.did)]

    def get_instance_graphql_uri(self, iid:str) -> str:
        return self._get_etcd_value(WorkflowInstanceKeys.ui_server_uri_key(iid))

    def get_instance_status(self, iid:str) -> str:
        status = self._get_etcd_value(WorkflowInstanceKeys.state_key(iid))
        return status or UNKNOWN

    def get_instance_meta_data(self, iid:str) -> list:
        meta = self._get_etcd_value(WorkflowInstanceKeys.metadata_key(iid))
        if meta is not None:
            return json.loads(meta)
        return None

    def _get_etcd_value(self, key:str):
        def __logic(etcd):
            ret, _ = etcd.get(key)
            if ret:
                return ret.decode('utf-8')
            return None

        return locked_call(key, __logic)

    def _put_etcd_value(self, key:str, data:Any):
        # data must be bytes
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, dict):
            data = json.dumps(data).encode()
        assert isinstance(data, bytes), 'Data must be bytes'

        def __logic(etcd):
            etcd.put(key, data)

        locked_call(key, __logic)


    def get_task_ids(self):
        return self.tasks.keys()

    def task(self, tid : str):
        if tid not in self.tasks.keys():
            return None
        return self.tasks[tid]

    def complete(self, iid : str, tid : str):
        assert tid in self.bridge_cfg, 'Configuration error - {tid} is not in BRIDGE_CONFIG'
        task = self.tasks[tid]
        for next_task in self.bridge_cfg[tid]: # handle more than one outbound edge
            logging.info(f'Firing edge {next_task}')
            # TODO: [REXFLOW-191] Either remove this duplicated code from app or here.
            next_headers = {
                Headers.X_HEADER_FLOW_ID: str(iid),
                Headers.X_HEADER_WORKFLOW_ID: str(self.did),
                'content-type': 'application/json',
                Headers.X_HEADER_TASK_ID: next_task['next_task_id_header'],
            }

            if iid in self.instance_headers.keys():
                for header in self.instance_headers[iid]:
                    key,val = header.split(':')
                next_headers[key] = val

            # initialize the data JSON to pass to the next step in the workflow.
            # This is at least the data that was passed in to this task, but we
            # need to append the form data collected here.
            data = {}
            for fld in task.get_form(iid):
                if not is_ignored_data_type(fld[TYPE]):
                    data[fld[DATA_ID]] = fld[DATA]
            if iid in self.instance_data:
                data.update(self.instance_data[iid])
            logging.info(f'-- next_task {next_task}\n-- headers {next_headers}\n-- data {data}')

            # in the use case that this ui-bridge is also the next client in the
            # workflow chain (as in two user tasks linked directly together), we've
            # found that calling ourselves directly results in Bad Things(tm). So,
            # we make this call in another thread to avoid this.
            req = PostRequest(self, next_task, next_headers, data)
            thd = threading.Thread(target=req)
            thd.start()
            return req.guid

    def set_post_response(self, guid:str, response):
        self.reponses[guid] = response

    def get_post_response(self, guid:str):
        return self.responses.get(guid, None)

    def get_wf_map(self):
        """
        Pull the current workflow map from flowd. This allows us to map generic workflow names to specific workflow
        deployments.
        """
        try:
            resp = requests.get(f'http://{self.flowd_host}:9002/wf_map')
            """
            {'message': 'Ok',
             'status': 0,
             'wf_map': {'AmortTable': [{'id': 'amorttable-8135e8f8',
                            'start_event_urls': ['http://start-startevent-1-amorttable-8135e8f8.amorttable-8135e8f8:5000/'],
                            'user_opaque_metadata': {}}]}}
            """
            return resp.json()['wf_map']
        except Exception as exn:
            logging.exception(
                f"failed making a call to {next_task['k8s_url']} on wf {iid}\nheaders:{next_headers}", #\ndata:{data}",
                exc_info=exn,
            )

class WorkflowTask:
    def __init__(self, wf:Workflow, tid:str):
        self.wf = wf
        self.tid = tid
        self._fields = {}   # the immutable complete set of form information
        self._values = {}   # the immutable initial set of form data
        self._has_persistent_fields = False
        form, _ = wf.etcd.get(WorkflowKeys.field_key(wf.did,tid))
        if form:
            self._fields = self._normalize_fields(form)
            for k,v in self._fields.items():
                self._values[k] = v[DATA]
                if not is_ignored_data_type(v[TYPE]):
                    self._has_persistent_fields = True
        logging.info(f'task {self.tid} has_persistent_fields {self._has_persistent_fields}')

    def has_persistent_fields(self):
        return self._has_persistent_fields

    def get_form(self, iid:str, reset:bool = False):
        """
        If iid is not provided, pull the form for the task. Otherwise
        pull the task form for the given iid. If the iid record does not exist,
        create the iid form from the did form master.
        """
        tid_key = WorkflowKeys.field_key(self.wf.did,self.tid)
        if iid:
            iid_key = WorkflowInstanceKeys.task_form_key(iid,self.tid)
            form, _ = self.wf.etcd.get(iid_key)
            if form is None:
                form, _ = self.wf.etcd.get(tid_key)
                self.wf._put_etcd_value(iid_key, form)
                logging.info(f'Form for {iid_key} did not exist - {form}')
                reset = True # run any initializers since we're creating the form
        else:
            form, _ = self.wf.etcd.get(tid_key)

        form = list(self._normalize_fields(form).values())

        if reset:
            """
            If any fields have default's defined, execute them
            """
            eval_locals = None  # lazy init
            for fld in form:
                if DEFAULT in fld:
                    logging.info(f'Field {fld[DATA_ID]} has default initializer {fld[DEFAULT]}')
                    initr = fld[DEFAULT]
                    if TYPE in initr and VALUE in initr:
                        if initr[TYPE] == EVAL:
                            if eval_locals is None: # lazy init
                                eval_locals = self.field_vals(iid)
                                eval_locals['req_json'] = self.wf.get_instance_data(iid)
                            logging.info(f'Evaluating {initr[VALUE]} with eval_locals {eval_locals}')
                            fld[DATA] = json.dumps(eval(initr[VALUE], {}, eval_locals))
                            logging.info(f'{fld[DATA_ID]} default is {fld[DATA]}')
                        elif initr[TYPE] == TEXT:
                            fld[DATA] = initr[VALUE]
        return form

    def update(self, iid:str, in_fields:list):
        # get the current fields into a dict for easy access!
        tmp = self.get_form(iid)
        flds = {}
        for f in tmp:
            flds[f[DATA_ID]] = f
        for f in in_fields:
            flds[f[DATA_ID]][DATA] = f[DATA]
        key = WorkflowInstanceKeys.task_form_key(iid,self.tid)
        val = json.dumps(list(flds.values()))

        self.wf._put_etcd_value(key, val)

        return flds

    def _normalize_fields(self, form:str) -> Dict[str, Any]:
        """
        graphql provides booleans as strings, so convert them to their python equivalents.
        """
        fields = {}
        field_list = json.loads(form.decode('utf-8'))
        for field in field_list:
            field[ENCRYPTED] = bool(field[ENCRYPTED])
            fields[field[DATA_ID]] = field
        return fields

    def fields(self, iid:str = None) -> List[Any]:
        """
        Return the fields for this task. If iid is provided, pull
        the values for the iid and return a deep copy of the fields
        for the i.
        """
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

    def field_vals(self, iid:str) -> Dict[str,any]:
        ret = {}
        fields = self.fields(iid)
        for fld in fields:
            ret[fld[DATA_ID]] = fld[DATA]
        return ret

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
    x = Workflow(did, 'a:b:c'.split(':'), 'localhost', 9001)
    x.start()
    x.notify_prism_iid_complete("http://localhost:8000/callback", iid, BStates.COMPLETED)
    etcd = etcd_utils.get_etcd()
    keys = WorkflowInstanceKeys(iid)
    etcd.put(keys.ui_server_uri_key(iid), "http://localhost:8000/callback")
    time.sleep(5)
    etcd.put(keys.state, BStates.RUNNING)
    etcd.put(keys.state, BStates.COMPLETED)
    print('hello')

