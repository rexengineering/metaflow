from prototypes.flowc.flowcode import workflow, service_task

@service_task()
def hello_task():
    return "Hello, world!"

@workflow
def hello_workflow():
    result = hello_task()
