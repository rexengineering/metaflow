from concurrent.futures import ThreadPoolExecutor
import json
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

EXPECTED = {
    "cashflow": "Positive!",
    "sauce": "Applied.",
    "underpants": "Collected.",
}

BPMN_FILE = 'data/test1_simple.bpmn'

# Just hammer it...make sure it's sturdy
NUM_REQUESTS = 200
NUM_THREADS = 20


class Test1(IntegrationTest):
    def __init__(self):
        self._name = "test1_simple_underpants"
        self._status = TestStatus('not_set_up')
        self._wf_id = None

    def setup(self) -> SetupResult:
        # Step 1: apply wf
        result = None
        out = flowctl("apply data/test1_simple.bpmn -o")
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
        '''We run several tests against the WF Deployment: First, we verify we can run
        one instance alone; then, we do stress-testing and run 100 instances in a row.
        '''
        self._status.set_state('running')
        result = [self.test_a()]
        result.extend(self.test_b())
        self._status.set_state('completed')
        return result

    def test_a(self) -> TestResult:
        # Step 1: Run an instance
        run_response = flowctl("run " + self._wf_id + " '{}' -o")
        instance_id = run_response['id']

        # Step 2: Wait for instance to complete. If slower than 1s, we fail.
        time.sleep(1)
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        # Step 3: Interrogate the Instance Output
        result_json = json.loads(instance['result'])

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        if result_json != EXPECTED:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        return TestResult([instance_id], 0, "Ok.", self._name)


    def test_b(self) -> List[TestResult]:
        '''Runs 200 instances in quick succession in order to stress-test the Envoys and Flowd.
        '''
        results = None
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            results = executor.map(lambda _: self.test_a(), range(NUM_REQUESTS))
        return [r for r in results]

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id], -1, f"Failed to clean up wf {self._wf_id}.")

    def status(self) -> TestStatus:
        return self.status
