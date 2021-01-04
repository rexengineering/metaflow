from typing import Callable

class Workflow:
    pass

class ServiceTask:
    pass

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
