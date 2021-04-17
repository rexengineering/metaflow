import json
import logging

from ariadne import ObjectType
from .flowd_api import Workflow, WorkflowTask

mutation = ObjectType("Mutation")
task_mutation = ObjectType("TaskMutation")

# Workflow Mutations

@mutation.field('createInstance')
def mutation_create_instance(_,info):
    workflow = info.context['workflow']
    response = workflow.create_instance()
    data = json.loads(response.data)
    #data: {"id": "process-0p1yoqw-aa16211c-9f5251689f1811eba4489a05f2a68bd3", "message": "Ok", "status": 0}
    ret = {}
    ret['did'] = workflow.did
    ret['iid'] = data['id']
    ret['status'] = 'SUCCESS'
    ret['tasks'] = workflow.tasks.keys()
    return ret

# Task Mutations

@mutation.field('tasks')
def mutation_tasks(_,info):
    return task_mutation

@task_mutation.field('form')
def task_mutation_form(_,info,input):
    logging.info(f'task_mutation_form {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS', 'fields':[]}

@task_mutation.field('validate')
def task_mutation_validate(_,info,input):
    logging.info(f'task_mutation_validate {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS', 'validatorResults':[]}

@task_mutation.field('save')
def task_mutation_save(_,info,input):
    logging.info(f'task_mutation_save {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS', 'validatorResults':[]}

@task_mutation.field('complete')
def task_mutation_complete(_,info,input):
    logging.info(f'task_mutation_complete {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS'}

