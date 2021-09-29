from prototypes.jriehl.flowc.flowcode import workflow, service_task

@service_task()
def hello_arg_task(name: str) -> str:
    return f'Hello, {name}!'

@workflow
def hello_arg_workflow():
    result0 = hello_arg_task('test subject')
    result1 = hello_arg_task(result0)
    result2 = hello_arg_task(name='Joe Bob')
    result3 = hello_arg_task(name=result2)
