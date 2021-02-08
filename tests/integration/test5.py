'''This file runs a test to verify that we can have multiple workflows deployed using the
same preexisting microservices, eg. we can have multiple different workflows all make calls
to the same Salesforce-Api pod.
'''
from concurrent.futures import ThreadPoolExecutor
import json
import os
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

NUM_REQUESTS = 20
NUM_THREADS = 20
# Generous wait period (in seconds). Keep it generous so that this can pass reliably even
# if the test environment is quite skimpy.
WAIT_PERIOD = 3

BPMN_FILE_A = 'data/test5_a.bpmn'
BPMN_FILE_B = 'data/test5_b.bpmn'

EXPECTED_A = {
    "cashflow": "Positive!",
    "sauce": "Applied.",
    "underpants": "Collected.",
}

EXPECTED_B = {
    "sauce": "Applied.",
    "underpants": "Collected.",
}

YAML_FILE = "data/test5_sauce.yaml"


class Test5(IntegrationTest):
    def __init__(self):
        self._name = "test5_heterogeneous"
        self._status = TestStatus('not_set_up')
        self._wf_id_a = "test5-a"
        self._wf_id_b = "test5-b"

    def setup(self) -> SetupResult:
        # Set up preexisting services
        os.system(f"./inject_and_deploy.sh {YAML_FILE}")

        result = None
        self.wf_id_a = flowctl(f"apply {BPMN_FILE_A} -o")
        self.wf_id_b = flowctl(f"apply {BPMN_FILE_B} -o")
        wf_ids = [self.wf_id_a, self.wf_id_b]

        # Step 2: wait for deployment to come up
        if not wait_for_status(self._wf_id_a, 'RUNNING') or \
                not wait_for_status(self._wf_id_b, 'RUNNING'):
            result = SetupResult(
                wf_ids, -1, "WF Deployment failed to come up."
            )
            self._status.set_state("setup_error")
        else:
            result = SetupResult(wf_ids, 0, "Ok.")
            self._status.set_state("set_up")

        return result

    def run(self) -> List[TestResult]:
        self._status.set_state('running')
        a_instances = None
        b_instances = None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            result_a = executor.map(
                lambda _: self.run_instance(self._wf_id_a, EXPECTED_A), range(NUM_REQUESTS)
            )
            result_b = executor.map(
                lambda _: self.run_instance(self._wf_id_b, EXPECTED_B), range(NUM_REQUESTS)
            )
            a_instances = [item for item in result_a]
            b_instances = [item for item in result_b]

        self._status.set_state('completed')
        return a_instances + b_instances

    def run_instance(self, wf_id, expected):
        instance_id = flowctl("run " + wf_id + " '{}' -o")['id']

        # Wait a generous 1 second for instance to complete
        time.sleep(WAIT_PERIOD)

        instance = flowctl(f"ps {instance_id} -o")[instance_id]

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        result_json = json.loads(instance['result'])
        if result_json != expected:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        return TestResult([instance_id], 0, "Ok.", "Heterogeneous WF.")

    def cleanup(self) -> CleanupResult:
        os.system(f"kubectl delete -f {YAML_FILE}")
        if cleanup_wf_deployment(self._wf_id_a) and cleanup_wf_deployment(self._wf_id_b):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id_a, self._wf_id_b], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id_a, self._wf_id_b], -1, "Failed to clean up WF's.")

    def status(self) -> TestStatus:
        return self.status
