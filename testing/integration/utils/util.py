import json
from subprocess import check_output
import time


def flowctl(command):
    command = ["python", "-m", "flowctl"] + command.split()
    result = check_output(command)
    if command[-1] == '-o':
        response = json.loads(result.decode())
    else:
        response = {}
    return response


def wait_for_status(wf_id, status, timeout_seconds=60):
    time_waited = 0
    interval = 5
    while time_waited < timeout_seconds:
        time.sleep(interval)
        time_waited += interval

        response = flowctl(f'ps -k DEPLOYMENT {wf_id} -o')

        current_status = response[wf_id]['state']

        if current_status == status:
            return True
    
    return False