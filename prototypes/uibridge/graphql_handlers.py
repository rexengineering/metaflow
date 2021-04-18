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
def task_mutation_form(_, info, input):
    try:
        task = info.context['workflow'].task(input['tid'])
        fields = task.fields()
        return {'iid':input['iid'], 'tid':input['tid'], 'status':'SUCCESS', 'fields':fields}
    except Exception as ex:
        print(ex)
        return {'iid':input['iid'], 'tid':input['tid'], 'status': 'FAILURE', 'fields':[]}

@task_mutation.field('validate')
def task_mutation_validate(_,info,input):
    task = info.context['workflow'].task(input['tid'])
    field_results = []
    all_passed = True
    for in_field in input['fields']:
        # here we will need to run the data from the corresponding input.field through
        # the validator(s) provided by field.validators to determine the result. For
        # now balk
        try:
            task_field = task.field(in_field['id'])
            results = []
            field_passed = True
            for validator in task_field['validators']:
                # ValidatorResult
                passed = True #validator.result
                field_passed = field_passed and passed #= validator.result
                results.append({'validator':validator['type'], 'passed':passed, 'result':'It\'s a good show!'})
            # FieldValidationResult
            field_results.append({'field':in_field['id'], 'passed': field_passed, 'results':results})
            all_passed = all_passed and field_passed
        except Exception as ex:
            print(ex)
    # TaskValidatePayload
    return {'iid':input['iid'], 'tid':input['tid'],'passed':all_passed, 'status':'SUCCESS', 'results':field_results}

@task_mutation.field('save')
def task_mutation_save(_,info,input):
    logging.info(f'task_mutation_save {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS', 'validatorResults':[]}

@task_mutation.field('complete')
def task_mutation_complete(_,info,input):
    logging.info(f'task_mutation_complete {input["iid"]} {input["tid"]}')
    return {'iid':'wf_instance_id','tid':'task1','status':'SUCCESS'}

