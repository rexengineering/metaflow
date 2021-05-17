# resolvers for mutations defined here
# Note: query resolvers are in resolvers.py
import logging

from ariadne import ObjectType
from .flowd_api import Workflow, WorkflowTask

# instantiate the mutation objects here. If you add another one,
# you need to add it to the initializer list in app.py
mutation = ObjectType("Mutation")
session_mutation = ObjectType("SessionMutations")
session_state_mutations = ObjectType("StateMutations")
workflow_mutations = ObjectType("WorkflowMutations")
task_mutations = ObjectType("TasksMutations")

# Session mutations

@mutation.field('session')
def mutation_session_mutations(_,info):
    return session_mutation

@session_mutation.field('start')
def session_mutation_start(_,info):
    print('session_mutation_start')
    return {'status':'SUCCESS'}

@session_mutation.field('state')
def session_mutation_status(_,info):
    print ('session_mutation_status')
    return session_state_mutations

@session_mutation.field('close')
def session_mutation_close(_,info):
    print ('session_mutation_close')
    return {'status':'SUCCESS','errors':[]}

@session_state_mutations.field('update')
def session_state_mutation_update(_,info,input):
    print(f'session_state_mutation_update {input}')
    return {'status':'SUCCESS', 'state':'RUNNING', 'errors':[]}

# Workflow Mutations

@mutation.field('workflow')
def mutation_workflow(_,info):
    return workflow_mutations

@workflow_mutations.field('start')
def workflow_mutations_start(_,info,input):
    workflow = info.context['workflow']
    response = workflow.create_instance()
    logging.info(response)
    return {'status':'SUCCESS', 'response':response}

@workflow_mutations.field('complete')
def workflow_mutations_complete(_,info,input):
    print(f'workflow_mutations_complete {input}')
    return {'status':'SUCCESS'}

# Task Mutations
@workflow_mutations.field('tasks')
def workflow_mutations_complete(_,info):
    return task_mutations

@task_mutations.field('start')
def task_mutations_start(_,info,input=None):
    return {'status':'SUCCESS'}

@task_mutations.field('validate')
def task_mutations_validate(_,info,input=None):
    print(f'task_mutations_validate {input}')
    return {'status':'SUCCESS'}

@task_mutations.field('save')
def task_mutations_save(_,info,input):
    print(f'task_mutations_save {input}')
    return {'status':'SUCCESS'}

@task_mutations.field('complete')
def task_mutations_complete(_,info,input):
    print(f'task_mutations_complete {input}')
    return {'status':'SUCCESS'}

