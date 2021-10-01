from prototypes.flowc.flowcode import service_task, workflow

@service_task()
def hello2_task():
    return 'Hello, ', 'world!'

@workflow
def hello2_workflow():
    hello, world = hello2_task()
