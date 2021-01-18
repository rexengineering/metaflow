from prototypes.jriehl.flowc.flowcode import workflow, service_task

@service_task()
def hello3_task():
    return "Hello, world!"

@workflow
def hello3_workflow():
    hello3_task()
