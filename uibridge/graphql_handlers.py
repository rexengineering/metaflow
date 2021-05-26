from flowlib.constants import WorkflowInstanceKeys
import json
import logging
import typing
from .validators import validator_factory
from . import graphql_wrappers as gql
from .graphql_wrappers import (
    DATA,
    DID,
    FAILURE,
    FIELDS,
    GRAPHQL_URI,
    DATA_ID,
    IID,
    PASSED,
    RESET,
    RESULTS,
    SUCCESS, 
    TID,
    TYPE,
    VALIDATORS,
    WORKFLOW,
)
from typing import List, Dict, Tuple

from ariadne import ObjectType

from .flowd_api import Workflow, WorkflowTask

query = ObjectType("Query")
mutation = ObjectType("Mutation")
task_mutation = ObjectType("TaskMutation")

# Queries

@query.field('getInstances')
def mutation_get_instance(_,info, input=None):
    workflow = info.context[WORKFLOW]
    status = workflow.get_status()
    if input and input[IID]:
        iid_list = [input[IID]]
    else:
        iid_list = workflow.get_instances()

    iid_info = []
    for iid in iid_list:
        uri = workflow.get_instance_graphql_uri(iid)
        status = workflow.get_instance_status(iid)
        iid_info.append(gql.workflow_instance_info(iid, status, uri))
    return gql.get_instances_payload(workflow.did, status, iid_info, workflow.get_task_ids())

# Workflow Mutations

@mutation.field('createInstance')
def mutation_create_instance(_,info,input):
    workflow = info.context[WORKFLOW]
    #data: {"id": "process-0p1yoqw-aa16211c-9f5251689f1811eba4489a05f2a68bd3", "message": "Ok", "status": 0}
    data = workflow.create_instance(input[GRAPHQL_URI])
    return gql.create_instance_payload(workflow.did, data['id'], SUCCESS, workflow.get_task_ids())

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
    reset = False if RESET not in input else input[RESET]
    form = []
    status = FAILURE
    if task:
        form = task.get_form(iid,reset)
        status = SUCCESS
        logging.info(form)
    return gql.task_form_payload(iid, input[TID], status, form)

@task_mutation.field('validate')
def task_mutation_validate(_,info,input):
    task = info.context[WORKFLOW].task(input[TID])
    all_passed, field_results = _validate_fields(task, input[IID], input[FIELDS])
    return gql.task_validate_payload(input[IID], input[TID], SUCCESS, all_passed, field_results)

@task_mutation.field('save')
def task_mutation_save(_,info,input):
    status = FAILURE
    tid    = input[TID]
    iid    = input[IID]
    task   = info.context[WORKFLOW].task(tid)
    if task:
        all_passed, field_results = _validate_fields(task, iid, input[FIELDS])
        task.update(iid, input[FIELDS])
        status = SUCCESS
    return gql.task_validate_payload(iid, tid, status, all_passed, field_results)

@task_mutation.field('complete')
def task_mutation_complete(_,info,input):
    logging.info(f'task_mutation_complete {input[IID]} {input[TID]}')
    # notify rexflow to continue the workflow
    workflow = info.context[WORKFLOW]
    workflow.complete(input[IID], input[TID])
    return gql.task_complete_payload(input[IID], input[TID], SUCCESS)

def _validate_fields(task:WorkflowTask, iid:str, fields:List) -> Tuple[bool, List]:
    # pull the current values for all fields from the backstore
    logging.info(f'_validate_fields {iid} {fields}')
    eval_locals = task.field_vals(iid)

    # overlay the values form the validator input over the persisted values
    # to give a currently 'proposed' form value set
    for in_field in fields:
        logging.info(f'updating {in_field[DATA_ID]} {eval_locals[in_field[DATA_ID]]} with {in_field[DATA]}')
        eval_locals[in_field[DATA_ID]] = in_field[DATA]
    logging.info(eval_locals)

    field_results = []
    all_passed = True # assume all validators for all fields pass
    for in_field in fields:
        # TODO: handle decryption here if in_field is marked encrypted
        field_id = in_field[DATA_ID]
        try:
            task_field = task.field(field_id)
            results = []
            field_passed = True # assume all validators on this field pass
            logging.info(f'validating field {in_field} {task_field[VALIDATORS]}')
            for validator in task_field[VALIDATORS]:
                # TODO: don't call validator_factory here. Prior to us getting here
                # task_field[VALIDATORS] should already be populated with objects
                # of BaseValidator-derived classes
                try:
                    vdor = validator_factory(validator)
                    if vdor is None:
                        raise NotImplementedError(f'Bad validator type \'{validator[TYPE]}\'')
                    vdor_passed  = vdor.validate(in_field[DATA], eval_locals)
                    field_passed = field_passed and vdor_passed
                    results.append(gql.validator_result(vdor.as_validator(), vdor_passed, vdor.message()))
                except Exception as ex:
                    results.append(gql.validator_result(validator, False, ex))
                    continue

            field_results.append(
                gql.field_validation_result(field_id, field_passed, results)
            )

            all_passed = all_passed and field_passed
        except Exception as ex:
            print('_validate_fields',ex)
            field_results.append(gql.field_validation_result(field_id, False, ex))
            field_passed = all_passed = False

    return (all_passed, field_results)
