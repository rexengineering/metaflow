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


class TestResult:
    def __init__(self, instance_ids: List[str], status: int, msg: str, name: str):
        self._instance_ids = instance_ids
        self._status = status
        self._message = msg
        self._name = name

    @property
    def message(self):
        return self._message

    @property
    def status(self):
        return self._status

    @property
    def instance_ids(self):
        return self._instance_ids

    @property
    def name(self):
        return self._name


class CleanupResult:
    def __init__(self, wf_ids: List[str], status: int, msg: str):
        self._wf_ids = wf_ids
        self._status = status
        self._message = msg

    @property
    def message(self):
        return self._message

    @property
    def status(self):
        return self._status

    @property
    def wf_ids(self):
        return self._wf_ids


class SetupResult:
    def __init__(self, wf_ids: List[str], status: int, msg: str):
        self._wf_ids = wf_ids
        self._status = status
        self._message = msg

    @property
    def message(self):
        return self._message

    @property
    def status(self):
        return self._status

    @property
    def wf_ids(self):
        return self._wf_ids


TEST_STATES = [
    'not_set_up',
    'setup_error',
    'set_up',
    'running',
    'completed',
    'cleaned_up',
]


class TestStatus:
    def __init__(self, state):
        assert state in TEST_STATES
        self._test_results = []
        self._setup_results = []
        self._cleanup_results = []
        self._state = state

    @property
    def test_results(self) -> List[TestResult]:
        return self._test_results

    @property
    def cleanup_results(self) -> List[CleanupResult]:
        return self._cleanup_results

    @property
    def setup_results(self) -> List[SetupResult]:
        return self._setup_results

    @property
    def state(self) -> str:
        return self._state

    def add_setup_result(self, sr: SetupResult):
        self._setup_results.append(sr)

    def add_cleanup_result(self, cr: CleanupResult):
        self._cleanup_results.append(cr)

    def add_test_result(self, tr: TestResult):
        self._test_results.append(tr)

    def set_state(self, state):
        assert state in TEST_STATES
        self._state = state


class IntegrationTest:
    def __init__(self):
        '''Init may or may not be overriden by implementation.
        '''
        self._name = None

    def setup(self) -> SetupResult:
        '''Sets up the WF Deployments and any other k8s objects necessary to run this
        integration test.
        '''
        assert False, "Must be overriden by implementation."

    def run(self) -> List[TestResult]:
        '''Runs one or more integration tests on the WF Deployment.
        '''
        assert False, "Must be overriden by implementation."

    def cleanup(self) -> CleanupResult:
        '''Cleans up the WF Deployment and any other k8s objects created by setup().
        '''
        assert False, "Must be overriden by implementation."

    def status(self) -> TestStatus:
        assert False, "Must be overriden by implementation."

    def name(self) -> str:
        return self._name
