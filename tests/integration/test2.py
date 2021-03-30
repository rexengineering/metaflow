import json
import os
from subprocess import check_output
import time
from typing import List

from util import (
    CleanupResult,
    IntegrationTest,
    SetupResult,
    TestResult,
    TestStatus,
    cleanup_wf_deployment,
    flowctl,
    wait_for_status,
)

BPMN_FILE = 'data/test2_conditional.bpmn'

# Generous wait period (in seconds). Keep it generous so that this can pass reliably even
# if the test environment is quite skimpy.
WAIT_PERIOD = 3


class Test2(IntegrationTest):
    def __init__(self):
        self._name = "test2_conditional"
        self._status = TestStatus('not_set_up')
        self._wf_id = None

    def setup(self) -> SetupResult:
        # Step 1: apply wf
        result = None
        out = flowctl(f"apply {BPMN_FILE} -o")
        wf_id = out['wf_id']

        # Step 2: wait for deployment to come up
        if not wait_for_status(wf_id, 'RUNNING'):
            result = SetupResult([wf_id], -1, f"WF Deployment '{wf_id}' failed to come up.")
            self._status.set_state("setup_error")
        else:
            result = SetupResult([wf_id], 0, "Ok.")
            self._status.set_state("set_up")

        self._wf_id = wf_id
        return result

    def run(self) -> List[TestResult]:
        '''We run two tests: one where we have enough `val` to profit (anything >= 137),
        and one where we don't have enough `val` to profit.
        '''
        self._status.set_state('running')
        result = [self.test_a(), self.test_b()]
        self._status.set_state('completed')
        return result

    def test_a(self) -> TestResult:
        # Step 1: Run an instance
        run_response = None
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', '{"val": 1}',
                f"http://localhost:80/start-test2",
            ], stderr=devnull)

        instance_id = json.loads(run_response.decode())['id']

        # Step 2: Wait for instance to complete. If slower than 1s, we fail.
        time.sleep(WAIT_PERIOD)
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        # Step 3: Interrogate the Instance Output
        result_json = json.loads(instance['result'])

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        if instance['end_event'] != 'end-didnot-profit':
            return TestResult([instance_id], -1, "Wrong Gateway evaluation.", self._name)

        if result_json != {"val": 2}:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        return TestResult([instance_id], 0, "Ok.", "Conditional: False")

    def test_b(self) -> List[TestResult]:
        # Step 1: Run an instance
        run_response = None
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', '{"val": 137}',
                "http://localhost:80/start-test2",
            ], stderr=devnull)
        instance_id = json.loads(run_response.decode())['id']

        # Step 2: Wait for instance to complete. If slower than 1s, we fail.
        time.sleep(WAIT_PERIOD)
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        # Step 3: Interrogate the Instance Output
        result_json = json.loads(instance['result'])

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        if result_json != {"val": 138, "cashflow": "Positive!"}:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        if instance['end_event'] != 'end-did-profit':
            return TestResult([instance_id], -1, "Wrong Gateway evaluation.", self._name)

        return TestResult([instance_id], 0, "Ok.", "Conditional: True")

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id], -1, f"Failed to clean up wf {self._wf_id}.")

    def status(self) -> TestStatus:
        return self.status
