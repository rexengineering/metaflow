import json
import logging
from subprocess import check_output
import time
from typing import List


def flowctl(command: str):
    command = ["python", "-m", "flowctl"] + command.split()
    result = check_output(command)
    if command[-1] == '-o':
        response = json.loads(result.decode())
    else:
        response = {}
    return response


def wait_for_status(wf_id: str, status: str, timeout_seconds: int = 60):
    assert timeout_seconds > 0, "Must have greater than 0 second timeout."
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


def test_result(wf_ids: List[str], instance_ids: List[str], status: int, msg: str) -> dict:
    return {
        "wf_ids": wf_ids,
        "instance_ids": instance_ids,
        "status": status,
        "message": msg,
    }


def cleanup_wf_deployment(wf_id):
    logging.info(f"Cleaning up deployment {wf_id}.")
    flowctl(f"stop -k DEPLOYMENT {wf_id}")

    # Takes a long time for deployment to come down.
    if not wait_for_status(wf_id, "STOPPED", timeout_seconds=180):
        logging.warning(f"Failed to stop deployment {wf_id}.")
        return False

    # Delete and check that deletion worked.
    flowctl(f"delete -k DEPLOYMENT {wf_id}")
    time.sleep(3)
    response = flowctl(f"ps -k DEPLOYMENT {wf_id} -o")

    if response[wf_id] != {}:
        logging.warning(f"Failed to delete deployment {wf_id}.")
        return False

    return True
