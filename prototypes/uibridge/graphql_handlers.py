from flowlib.constants import WorkflowInstanceKeys
import json
import logging
import typing
from . import graphql_factory as gql
from .graphql_factory import (
    DID,
    FAILURE,
    FIELDS,
    ID,
    IID,
    PASSED,
    RESULTS,
    SUCCESS, 
    TID,
    VALIDATORS,
    WORKFLOW,
)
from typing import List, Dict, Tuple

from ariadne import ObjectType

from .flowd_api import Workflow, WorkflowTask

mutation = ObjectType("Mutation")
task_mutation = ObjectType("TaskMutation")

# Workflow Mutations

@mutation.field('createInstance')
def mutation_create_instance(_,info):
    workflow = info.context[WORKFLOW]
    response = workflow.create_instance()
    #data: {"id": "process-0p1yoqw-aa16211c-9f5251689f1811eba4489a05f2a68bd3", "message": "Ok", "status": 0}
    data = json.loads(response.data)
    return gql.create_instance_payload(workflow.did, data[ID], SUCCESS, workflow.get_task_ids())

@mutation.field('getInstances')
def mutation_get_instance(_,info):
    workflow = info.context[WORKFLOW]
    iid_list = workflow.get_instances()
    return gql.get_instances_payload(workflow.did, iid_list)
# Task Mutations

@mutation.field('tasks')
def mutation_tasks(_,info):
    return task_mutation

@task_mutation.field('form')
def task_mutation_form(_, info, input):
    '''
    Return the list of fields for the given tid. There are two copies of the 
    form - the immutable copy in the did, and the instance copy in the iid.

    Which one the caller receives depends on a few things:
    1. If the iid is provided, then the iid copy is returned, unless
       it does not exist, in which case it is created from the did copy.
    2. If the iid is not provided then the did copy is returned. Any iid
       copy is not affected.
    '''
    workflow = info.context[WORKFLOW]
    task = workflow.task(input[TID])
    iid = '' if IID not in input else input[IID]
    form = []
    status = FAILURE
    if task:
        form = task.get_form(iid)
        status = SUCCESS
    return gql.task_form_payload(iid, input[TID], status, form)

@task_mutation.field('validate')
def task_mutation_validate(_,info,input):
    task = info.context[WORKFLOW].task(input[TID])
    all_passed, field_results = _validate_fields(task, input[FIELDS])
    return gql.task_validate_payload(input[IID], input[TID], SUCCESS, all_passed, field_results)

@task_mutation.field('save')
def task_mutation_save(_,info,input):
    # run the input though the validator to make sure it's good
    iid = input[IID]
    tid = input[TID]
    task = info.context[WORKFLOW].task(tid)
    field_results = []
    status = FAILURE
    passed = False
    if task:
        # not all fields may have been passed in. Hence, we merge or update the 
        # provided fields into the stored image.
        fields = list(task.update(iid, input[FIELDS]).values())
        print(fields)
        passed, field_results = _validate_fields(task, fields)
        status = SUCCESS
    return gql.task_save_payload(iid, tid,  status, passed, field_results)

@task_mutation.field('complete')
def task_mutation_complete(_,info,input):
    logging.info(f'task_mutation_complete {input[IID]} {input[TID]}')
    return gql.task_complete_payload(input[IID], input[TID], SUCCESS)

def _validate_fields(task:WorkflowTask, fields:List) -> Tuple[bool, List]:
    field_results = []
    all_passed = True # assume all validators for all fields pass
    for in_field in fields:
        # TODO: handle decryption here if in_field is marked encrypted

        # here we will need to run the data from the corresponding input.field through
        # the validator(s) provided by field.validators to determine the result. For
        # now balk and all validators pass.
        try:
            field_id = in_field[ID]
            task_field = task.field(field_id)
            results = []
            field_passed = True # assume all validators on this field pass
            for validator in task_field[VALIDATORS]:
                passed = True #validator.result
                field_passed = field_passed and passed
                results.append(gql.validator_result(validator, passed, 'It\'s a fair cop!'))
            field_results.append(
                gql.field_validation_result(field_id, field_passed, results)
            )
            all_passed = all_passed and field_passed
        except Exception as ex:
            print('_validate_fields',ex)
    return (all_passed, field_results)
