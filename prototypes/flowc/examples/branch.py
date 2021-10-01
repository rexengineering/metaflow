import random

from prototypes.flowc.flowcode import service_task, workflow

@service_task()
def get_random():
    return random.random() < 0.6

@service_task()
def original_task():
    return {'result': 42}

@service_task()
def new_hotness():
    return {'result': 1729}

@workflow
def branch_example():
    rand_bool = get_random()
    if rand_bool:
        result_obj = original_task()
    else:
        result_obj = new_hotness()
    return result_obj
