from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class WorkflowInstanceId(str):
    '''Identifier for a workflow instance'''

class TaskId(str):
    '''Identifier for a task'''

class OperationStatus(str, Enum):
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'

class Problem(BaseModel):
    message: str

class StartTaskInput(BaseModel):
    iid: WorkflowInstanceId
    tid: TaskId

class StartTaskPayload(BaseModel):
    status: OperationStatus
    errors: Optional[List[Problem]]

class CompleteWorkflowInput(BaseModel):
    iid: WorkflowInstanceId

class CompleteWorkflowPayload(BaseModel):
    status: OperationStatus
    errors: Optional[List[Problem]]


