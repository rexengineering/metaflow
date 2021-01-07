from concurrent.futures import ThreadPoolExecutor
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


BPMN_FILE = 'data/test6_repeated.bpmn'
YAML_FILE = "data/test6_increment.yaml"

# Just hammer it...make sure it's sturdy
NUM_REQUESTS = 200
NUM_THREADS = 20

# Generous wait period (in seconds). Keep it generous so that this can pass reliably even
# if the test environment is quite skimpy.
WAIT_PERIOD = 3


class Test6(IntegrationTest):
    def __init__(self):
        self._name = "test6_repeated_call"
        self._status = TestStatus('not_set_up')
        self._wf_id = "test6"

    def setup(self) -> SetupResult:
        # Step 0: set up preexisting service
        os.system(f"./inject_and_deploy.sh {YAML_FILE}")

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
        '''We run several tests against the WF Deployment: First, we verify we can run
        one instance alone; then, we do stress-testing and run 100 instances in a row.
        '''
        self._status.set_state('running')

        results = None
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            results = executor.map(self.run_instance, range(NUM_REQUESTS))
        results = [r for r in results]
        self._status.set_state('completed')
        return results

    def run_instance(self, val) -> TestResult:
        # Step 1: Run an instance
        run_response = None
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', '{"val": ' + str(val) + '}',
                "http://localhost:80/start-test6-a66df261",
            ], stderr=devnull)

        instance_id = json.loads(run_response.decode())['id']

        # Step 2: Wait for instance to complete. If slower than WAIT_PERIOD, we fail.
        time.sleep(WAIT_PERIOD)
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        # Step 3: Interrogate the Instance Output
        if instance['state'] != 'COMPLETED':
            return TestResult(
                [instance_id],
                -1,
                f"Instance didn't complete: {instance['state']}.", self._name
            )

        result_json = json.loads(instance['result'])

        expected = {'sauce': 'Applied.', 'val': val + 2}
        if result_json != expected:
            return TestResult(
                [instance_id],
                -1,
                f"Result didn't match: {result_json} != {expected}.",
                self._name
            )

        return TestResult([instance_id], 0, "Ok.", self._name)

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id], -1, f"Failed to clean up wf {self._wf_id}.")

    def status(self) -> TestStatus:
        return self.status
