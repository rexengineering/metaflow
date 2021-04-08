# TODO: Stub out resolvers for queries and mutations defined in the schema.
from ariadne import ObjectType

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
    print( f'resolve_workflow_query_active {filter}', flush=True)
    return [{'iid':'wf_iid','did':'wf_did','status':'IN_PROGRESS','tasks':[{'id':'task_id','data':[], 'status':'IN_PROGRESS'}]}]


# session = ObjectType("Session")
# workflow_query = ObjectType("WorkflowQuery")
# workflow = ObjectType("Workflow")


# @query.field("session")
# def resolve_session(obj,info):
#     print(f'resolve_session {info.context}')
#     return session

# @session.field("id")
# def resolve_session_id(obj,info):
#     print(f'resolve_session_id {info.context}')
#     return "Session ID"

# @session.field("state")
# def resolve_session_state(obj,info):
#     print(f'resolve_session_state {info.context}')
#     return "good"

# @query.field("workflows")
# def resolve_workflows(obj,info):
#     print(f'resolve_workflows {type(obj)}')
#     return workflow_query

# @workflow_query.field("active")
# def resolve_workflow_query_active(obj,info,filter=None):
#     print(f'resolve_workflow_query_active {type(obj)}')
#     return [workflow]

# @workflow_query.field("available")
# def resolve_workflow_query_available(obj,info):
#     print(f'resolve_workflow_query_available {type(obj)}')
#     return ['hello','world']

# @workflow.field("iid")
# def resolve_workflow_iid(obj,info):
#     print(f'resolve_workflow_iid {type(obj)}')
#     return 'wf_iid'

# @workflow.field("did")
# def resolve_workflow_did(obj,info):
#     print(f'resolve_workflow_did {type(obj)}')
#     return 'wf_did'

# def get_workflow(iid,did):
#     workflow = ObjectType("Workflow")
#     return workflow