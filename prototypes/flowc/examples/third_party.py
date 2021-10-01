'''This is a proposed example of wrapping an existing service...
'''

import requests
from prototypes.flowc.flowcode import service_task, workflow

@service_task()
def hit_known_service(data):
    result = requests.post('https://3psystem.io/', data)
    return result.json()

@service_task()
def hit_other_service(data):
    if data['alice'] == 'spy':
        data['alice'] = 'housekeeper'
    result = requests.post('https://fbi.gov/', data)
    return result.json()

@workflow
def my_3p_workflow():
    result0 = hit_known_service({'bob': 'uncle'})
    result1 = hit_other_service({'result0': result0, 'alice': 'spy'})
