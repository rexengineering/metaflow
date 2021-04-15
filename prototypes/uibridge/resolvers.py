# resolvers for queries defined here
# Note: mutation resolvers are in mutations.py
import json
import typing
from ariadne import ObjectType
from flowlib import etcd_utils
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys

# instantiate the query objects here. If you add another one,
# you need to add it to the initializer list in app.py
query = ObjectType("Query")
workflow_query = ObjectType("WorkflowQuery")

@query.field('session')
def resolve_session(*_):
    return {'id':'sess_id','state':'good'}

@query.field('workflows')
def resolve_workflows(_, info, filter=None):
    return workflow_query

@workflow_query.field('active')
def resolve_workflow_query_active(_, info, filter=None):
    # pull tasks from etcd based on filter (if specified)
    etcd = etcd_utils.get_etcd()
    dids = etcd_utils.get_next_level(WorkflowKeys.ROOT)
    ret = []
    for did in dids:
        ret.append(rexflow_did_to_graphql(did))
    return ret

def rexflow_did_to_graphql(did:str) -> dict:
    '''
    given a REXFlow DID, pull the relevant data from etcd and build a
    dict containing a graphql Workflow object
    '''
    etcd = etcd_utils.get_etcd()
    keys = WorkflowKeys(did)
    ret = {}
    ret['iid'] = ''
    ret['did'] = did
    ret['status'] = (etcd.get(keys.state)[0]).decode('utf-8')
    ret['tasks'] = rexflow_did_tasks_to_graphql(did)
    return ret

def rexflow_did_tasks_to_graphql(did:str) -> list:
    etcd = etcd_utils.get_etcd()
    tasks = etcd_utils.get_next_level(WorkflowKeys.probe_key(did))
    print(tasks,flush=True)
    ret = []
    for tid in tasks:
        tdata = {}
        tdata['id'] = tid

        fields = etcd.get(WorkflowKeys.field_key(did,tid))[0]
        if fields:
            tdata['data'] = json.loads(fields.decode('utf-8'))
        else:
            tdata['data'] = []
        tdata['status'] = etcd.get(WorkflowKeys.task_key(did,tid))[0].decode('utf-8')
        ret.append(tdata)
    return ret

