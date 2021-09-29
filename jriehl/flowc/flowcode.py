import ast
from typing import Callable, Optional

class Workflow:
    pass

class ServiceTask:
    definition: Optional[ast.FunctionDef]

    def __init__(self) -> None:
        super().__init__()
        self.definition = None

def workflow(*args, **kws):
    def workflow_decorator(func: Callable):
        func._workflow = Workflow()
        return func
    if len(args) > 0 and isinstance(args[0], Callable):
        return workflow_decorator(args[0])
    return workflow_decorator

def service_task(*args, **kws):
    def service_task_decorator(func: Callable):
        func._service_task = ServiceTask()
        return func
    if len(args) > 0 and isinstance(args[0], Callable):
        return service_task_decorator(args[0])
    return service_task_decorator
