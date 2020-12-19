'''This file stress-tests the `flowctl start -k INSTANCE` code. We deploy a WF in which one
step fails 50% of the time, and we run 200 instances (and retry each one up to 18 times)
and verify that at the end, all of them have succeeded.
'''
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

BPMN_FILE = 'data/test4_retry.bpmn'

# Make sure we can handle high volume in short amount of time
NUM_REQUESTS = 200
NUM_THREADS = 40

# Generous wait period (in seconds)
WAIT_PERIOD = 1

# Ensures probability that one of the 200 instances doesn't complete is 0.1%.
MAX_RETRIES = 18

EXPECTED = {
    "cashflow": "Positive!",
    "sauce": "Applied.",
    "underpants": "Collected.",
}


class Test4(IntegrationTest):
    def __init__(self):
        self._name = "test4_retry"
        self._status = TestStatus('not_set_up')
        self._wf_id = "test4"

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
        self._status.set_state('running')
        instance_futures = None
        instances = None
        result_futures = None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            instance_futures = executor.map(self.run_instance, range(NUM_REQUESTS))
            instances = [item for item in instance_futures]

            # Retry each failed instances until they succeed.
            result_futures = executor.map(self.retry_instance, instances)

        out = [r for r in result_futures]
        self._status.set_state('completed')
        return out

    def run_instance(self, val):
        return flowctl("run " + self._wf_id + " '{}' -o")['id']

    def retry_instance(self, instance_id) -> TestResult:
        # Wait a few seconds for all the traffic to settle down.
        time.sleep(WAIT_PERIOD)

        instance = flowctl(f"ps {instance_id} -o")[instance_id]
        state = instance['state']

        attempts = 0
        while attempts < MAX_RETRIES and state == 'STOPPED':
            attempts += 1
            flowctl(f"start -k INSTANCE {instance_id}")
            time.sleep(WAIT_PERIOD)
            instance = flowctl(f"ps {instance_id} -o")[instance_id]
            state = instance['state']

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        result_json = json.loads(instance['result'])
        if result_json != EXPECTED:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        return TestResult([instance_id], 0, "Ok.", "Retry stress test.")

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id], -1, f"Failed to clean up wf {self._wf_id}.")

    def status(self) -> TestStatus:
        return self.status
