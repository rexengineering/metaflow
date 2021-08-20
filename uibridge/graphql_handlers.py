from uibridge.salesforce_utils import SalesforceManager
from flowlib.constants import WorkflowInstanceKeys
import json
import logging
import typing
from .validators import validator_factory
from . import graphql_wrappers as gql
from .graphql_wrappers import (
    is_ignored_data_type,
    DATA,
    DID,
    FAILURE,
    FIELDS,
    GRAPHQL_URI,
    DATA_ID,
    IID,
    KEY,
    META_DATA,
    PASSED,
    RESET,
    RESULTS,
    SUCCESS, 
    TID,
    TYPE,
    VALIDATORS,
    VALUE,
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
    in_meta = None
    iid_list = None
    if input:
        in_meta = input.get(META_DATA,None)
        if in_meta is not None:
            in_meta = {d[KEY]:d[VALUE] for d in in_meta}
        if IID in input:
            iid_list = [input[IID]]

    if iid_list is None:
        iid_list = workflow.get_instances(in_meta)

    iid_info = []
    for iid in iid_list:
        uri = workflow.get_instance_graphql_uri(iid)
        meta = workflow.get_instance_meta_data(iid)
        if meta is not None:
            meta = [
                gql.meta_data(k, v)
                for k,v in meta.items()
            ]
        iid_status = workflow.get_instance_status(iid)
        iid_info.append(gql.workflow_instance_info(iid, iid_status, meta, uri))
    return gql.get_instances_payload(workflow.did, status, iid_info, workflow.get_task_ids())

# Workflow Mutations

@mutation.field('createInstance')
def mutation_create_instance(_,info,input):
    workflow = info.context[WORKFLOW]
    #data: {"id": "process-0p1yoqw-aa16211c-9f5251689f1811eba4489a05f2a68bd3", "message": "Ok", "status": 0}
    meta = input.get(META_DATA, [])
    uri  = input[GRAPHQL_URI]
    did  = input.get(DID, None)
    data = workflow.create_instance(did, uri, meta)
    return gql.create_instance_payload(workflow.did, data['id'], SUCCESS, workflow.get_task_ids())

@mutation.field('cancelInstance')
def mutation_stop_instance(_, info, input):
    workflow = info.context[WORKFLOW]
    iid = input[IID]
    status = SUCCESS
    state = ''
    try:
        state = workflow.cancel_instance(iid)
    except ValueError:
        status = FAILURE
    return gql.cancel_instance_payload(workflow.did, iid, state, status)

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
    task  = workflow.task(input[TID])
    iid   = input.get(IID, '')
    reset = input.get(RESET, False)
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
    wf     = info.context[WORKFLOW]
    task   = wf.task(tid)
    sf     = info.context.get('salesforce', False)
    sf_mgr:SalesforceManager = info.context.get('sf_mgr', None)
    logging.info(f'Salesforce info {sf} {sf_mgr}')
    if task:
        all_passed, field_results = _validate_fields(task, iid, input[FIELDS])
        flds = task.update(iid, input[FIELDS])
        status = SUCCESS
        if sf:
            sf_mgr.post(iid, task, flds)
    return gql.task_validate_payload(iid, tid, status, all_passed, field_results)

@task_mutation.field('complete')
def task_mutation_complete(_,info,input):
    logging.info(f'task_mutation_complete {input[IID]} {input[TID]}')
    # notify rexflow to continue the workflow
    workflow = info.context[WORKFLOW]
    workflow.complete(input[IID], input[TID])
    return gql.task_complete_payload(input[IID], input[TID], SUCCESS)

def _validate_fields(task:WorkflowTask, iid:str, fields:List) -> Tuple[bool, List]:
    """
    Validate the fields vs its validators (if any.) The fields passed in may be
    a subset of all fields in the form for the task, and in this case fill in the
    blanks values from any stored form.

    Certain fields - such as WORKFLOW - are skipped.
    """
    # pull the current values for all fields from the backstore
    logging.info(f'_validate_fields {iid} {fields}')
    eval_locals = task.field_vals(iid)

    # overlay the values from the validator input over the persisted values
    # to give a currently 'proposed' form value set
    for in_field in fields:
        task_field = task.field(in_field[DATA_ID])
        if is_ignored_data_type(task_field[TYPE]):
            continue
        logging.info(f'updating {in_field[DATA_ID]} {eval_locals[in_field[DATA_ID]]} with {in_field[DATA]}')
        eval_locals[in_field[DATA_ID]] = in_field[DATA]
    logging.info(eval_locals)

    field_results = []
    all_passed = True # assume all validators for all fields pass
    for in_field in fields:
        field_id   = in_field[DATA_ID]
        task_field = task.field(field_id)
        # do not validate static fields
        if is_ignored_data_type(task_field[TYPE]):
            continue
        # TODO: handle decryption here if in_field is marked encrypted
        try:
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
