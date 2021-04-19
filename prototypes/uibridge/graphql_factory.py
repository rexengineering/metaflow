'''
Handles objects received from and sent to graphql queries and mutations
'''
import typing
from typing import Dict, List

CONSTRAINT = 'constraint'
DATA       = 'data'
DID        = 'did'
ENCRYPTED  = 'encrypted'
FIELD      = 'field'
FIELDS     = 'fields'
ID         = 'id'
IID        = 'iid'
IID_LIST   = 'iid_list'
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

SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'

def validator(type:str, constraint:str) -> Dict[str,any]:
    return {
        TYPE:type,
        CONSTRAINT:constraint
    }

def validator_result(validator:Dict[str,str], passed:bool, result:str):
    return {
        VALIDATOR: validator,
        PASSED: passed,
        RESULT: result,
    }

def field_validation_result(field:str, passed:bool, results:List):
    return {
        FIELD: field,
        PASSED: passed,
        RESULTS: results,
    }

def task_mutations_form_input(iid:str, tid:str):
    return {
        IID:iid,
        TID:tid,
    }

def task_field_input(id:str, type:str, data:str, encrypted:bool):
    return {
        ID: id,
        TYPE: type,
        DATA: data,
        ENCRYPTED: encrypted,
    }

def task_mutation_validate_input(iid:str, tid:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        FIELDS: fields
    }

def task_mutation_save_input(iid:str, tid:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        FIELDS: fields
    }

def task_mutation_complete_input(iid:str, tid:str):
    return {
        IID: iid,
        TID: tid
    }

def create_instance_payload(did:str, iid:str, status:str, tasks:List[str]):
    return {
        DID: did,
        IID: iid,
        STATUS: status,
        TASKS: tasks
    }

def get_instances_payload(did:str, iid_list:List[str]):
    return {
        DID: did,
        IID_LIST: iid_list
    }

def task_form_payload(iid:str, tid:str, status:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        STATUS: status,
        FIELDS: fields
    }

def task_validate_payload(iid:str, tid:str, status:str, passed:bool, results:List):
    return {
        IID: iid,
        TID: tid,
        STATUS: status,
        PASSED: passed,
        RESULTS: results
    }

def task_save_payload(iid:str, tid:str, status:str, passed:bool, results:List):
    # cheat - right now the TaskValidatePayload is the same as TaskSavePayload
    return task_validate_payload(iid, tid, status, passed, results)

def task_complete_payload(iid:str, tid:str, status:str):
    return {
        IID: iid,
        TID: tid,
        STATUS: status
    }

