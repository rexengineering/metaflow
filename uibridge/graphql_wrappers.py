"""
Convenience methods to create objects received from and sent to graphql 
queries and mutations
"""
import typing
from typing import Any, Dict, List

class DataType:
    COPY = 'COPY'
    TEXT = 'TEXT'
    CURRENCY = 'CURRENCY'
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    BOOLEAN = 'BOOLEAN'
    PERCENTAGE = 'PERCENTAGE'
    TABLE = 'TABLE'
    WORKFLOW = 'WORKFLOW'

# these are DataType's that are ignored in form processing
IGNORED_DATA_TYPES = [DataType.COPY, DataType.WORKFLOW]

def is_ignored_data_type(type:DataType) -> bool:
    return type in IGNORED_DATA_TYPES

# validator types
class Validator:
    BOOLEAN = 'BOOLEAN'
    INTERVAL = 'INTERVAL'
    PERCENTAGE = 'PERCENTAGE'
    POSITIVE = 'POSITIVE'
    REGEX = 'REGEX'
    REQUIRED = 'REQUIRED'

# graphql field names
BODY1      = 'BODY1'
CONSTRAINT = 'constraint'
CREATE_STOPPED = 'create_stopped'
DATA       = 'data'
DATA_ID    = 'dataId'
DEFAULT    = 'default'
DID        = 'did'
DID_STATUS = 'did_status'
ENCRYPTED  = 'encrypted'
EVAL       = 'EVAL'
FIELD      = 'field'
FIELDS     = 'fields'
GRAPHQL_URI= 'graphqlUri'
ID         = 'id'
IID        = 'iid'
IID_LIST   = 'iid_list'
IID_STATUS = 'iid_status'
KEY        = 'key'
LABEL      = 'label'
MESSAGE    = 'message'
META_DATA  = 'meta_data'
ORDER      = 'order'
PASSED     = 'passed'
RESET      = 'reset'
RESULT     = 'result'
RESULTS    = 'results'
STATUS     = 'status'
TASKS      = 'tasks'
TEXT       = 'TEXT'
TID        = 'tid'
TYPE       = 'type'
VALIDATOR  = 'validator'
VALIDATORS = 'validators'
VALUE      = 'value'
VARIANT    = 'variant'
WORKFLOW   = 'workflow'
UNKNOWN    = 'UNKNOWN'
XID        = 'xid'

SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'

def validator(type:str, constraint:str) -> Dict[str,Any]:
    return {
        TYPE:type,
        CONSTRAINT:constraint,
    }

def validator_result(validator:Dict[str,Any], passed:bool, message:str):
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

def meta_data(key:str, val:str):
    return {
        KEY: key,
        VALUE: val,
    }

def create_workflow_instance_input(iid: str, did:str, graphql_uri: str, meta:list):
    return {
        DID: did,
        GRAPHQL_URI: graphql_uri,
        META_DATA: meta,
    }

def cancel_workflow_instance_input(iid:str):
    return {
        IID: iid,
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

def start_instance_payload(did:str, iid:str, status:str, tasks:List[str]) -> dict:
    # we are using the same payload as create instance
    return create_instance_payload(did,iid,status,tasks)

def cancel_instance_payload(did:str, iid:str, state:str, status:str):
    return {
        DID: did,
        IID: iid,
        IID_STATUS: state,
        STATUS: status,
    }

def workflow_instance_info(iid:str, iid_status:str, meta:list, graphql_uri:str):
    return {
        IID: iid,
        IID_STATUS: iid_status,
        META_DATA: meta,
        GRAPHQL_URI: graphql_uri,
    }

def get_instances_payload(did:str, did_status:str, iid_list:List, tasks:List[str]):
    return {
        DID: did,
        DID_STATUS: did_status,
        IID_LIST: iid_list,
        TASKS: tasks,
    }

def field_initializer(type:str, value:str):
    return {
        TYPE: type,
        VALUE: value,
    }

def field_validator(type:str, constraint:str):
    return {
        TYPE: type,
        CONSTRAINT: constraint,
    }

def task_field_data(data_id:str, type:str, order:int, label:str, data:str, defval:dict, encrypted:bool, validators:List, variant:str = None):
    if type == TEXT and variant is None:
        variant = BODY1
    return {
        DATA_ID: data_id,
        TYPE: type,
        ORDER: order,
        LABEL: label,
        DATA: data,
        DEFAULT: defval,
        VARIANT: variant,
        ENCRYPTED: encrypted,
        VALIDATORS: validators,
    }

def task_form_payload(iid:str, tid:str, xid:str, status:str, fields:List):
    return {
        IID: iid,
        TID: tid,
        XID: xid,
        STATUS: status,
        FIELDS: fields,
    }

def task_validate_payload(iid:str, tid:str, xid:str, status:str, passed:bool, results:List):
    return {
        IID: iid,
        TID: tid,
        XID: xid,
        STATUS: status,
        PASSED: passed,
        RESULTS: results,
    }

def task_save_payload(iid:str, tid:str, status:str, passed:bool, results:List):
    # cheat - right now the TaskValidatePayload is the same as TaskSavePayload
    return task_validate_payload(iid, tid, status, passed, results)

def task_complete_payload(iid:str, tid:str, xid:str, status:str):
    return {
        IID: iid,
        TID: tid,
        XID: xid,
        STATUS: status,
    }

