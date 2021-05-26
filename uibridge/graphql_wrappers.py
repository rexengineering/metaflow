'''
Concenience methods to create objects received from and sent to graphql queries and mutations
'''
import typing
from typing import Dict, List

CONSTRAINT = 'constraint'
DATA       = 'data'
DATA_ID    = 'dataId'
DID        = 'did'
DID_STATUS = 'did_status'
ENCRYPTED  = 'encrypted'
FIELD      = 'field'
FIELDS     = 'fields'
GRAPHQL_URI= 'graphqlUri'
IID        = 'iid'
IID_LIST   = 'iid_list'
IID_STATUS = 'iid_status'
LABEL      = 'label'
MESSAGE    = 'message'
ORDER      = 'order'
PASSED     = 'passed'
RESULT     = 'result'
RESULTS    = 'results'
STATUS     = 'status'
TASKS      = 'tasks'
TID        = 'tid'
TYPE       = 'type'
VALIDATOR  = 'validator'
VALIDATORS = 'validators'
WORKFLOW   = 'workflow'
UNKNOWN    = 'UNKNOWN'

SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'

def validator(type:str, constraint:str) -> Dict[str,any]:
    return {
        TYPE:type,
        CONSTRAINT:constraint,
    }

def validator_result(validator:Dict[str,any], passed:bool, message:str):
    return {
        VALIDATOR: validator,
        PASSED: passed,
        MESSAGE: message,
    }

def field_validation_result(data_id:str, passed:bool, results:List):
    return {
        DATA_ID: data_id,
        PASSED: passed,
        RESULTS: results,
    }

def create_workflow_instance_input(iid: str, graphql_uri: str):
    return {
        GRAPHQL_URI: graphql_uri,
    }

def task_mutations_form_input(iid:str, tid:str):
    return {
        IID:iid,
        TID:tid,
    }

def task_field_input(data_id:str, data:str):
    return {
        DATA_ID: data_id,
        DATA: data,
    }

def task_mutation_validate_input(iid:str, tid:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        FIELDS: fields,
    }

def task_mutation_save_input(iid:str, tid:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        FIELDS: fields,
    }

def task_mutation_complete_input(iid:str, tid:str):
    return {
        IID: iid,
        TID: tid,
    }

def create_instance_payload(did:str, iid:str, status:str, tasks:List[str]):
    return {
        DID: did,
        IID: iid,
        STATUS: status,
        TASKS: tasks,
    }

def workflow_instance_info(iid:str, iid_status:str, graphql_uri:str):
    return {
        IID: iid,
        IID_STATUS: iid_status,
        GRAPHQL_URI: graphql_uri,
    }

def get_instances_payload(did:str, did_status:str, iid_list:List, tasks:List[str]):
    return {
        DID: did,
        DID_STATUS: did_status,
        IID_LIST: iid_list,
        TASKS: tasks,
    }

def field_validator(type:str, constraint:str):
    return {
        TYPE: type,
        CONSTRAINT: constraint,
    }

def task_field_data(data_id:str, type:str, order:int, label:str, data:str, encrypted:bool, validators:List):
    return {
        DATA_ID: data_id,
        TYPE: type,
        ORDER: order,
        LABEL: label,
        DATA: data,
        ENCRYPTED: encrypted,
        VALIDATORS: validators,
    }

def task_form_payload(iid:str, tid:str, status:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        STATUS: status,
        FIELDS: fields,
    }

def task_validate_payload(iid:str, tid:str, status:str, passed:bool, results:List):
    return {
        IID: iid,
        TID: tid,
        STATUS: status,
        PASSED: passed,
        RESULTS: results,
    }

def task_save_payload(iid:str, tid:str, status:str, passed:bool, results:List):
    # cheat - right now the TaskValidatePayload is the same as TaskSavePayload
    return task_validate_payload(iid, tid, status, passed, results)

def task_complete_payload(iid:str, tid:str, status:str):
    return {
        IID: iid,
        TID: tid,
        STATUS: status,
    }

