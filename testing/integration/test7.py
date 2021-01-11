'''This file runs a test to verify that we can:
1. Throw an event to kafka upon workflow completion
2. Start a WF Instance by listening to Kafka.
'''
from concurrent.futures import ThreadPoolExecutor
import json
import os
from subprocess import check_output
import time
from typing import List
import uuid

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

# Smaller number of requests here, since checking for correctness is N^2. This isn't really
# a stress test but rather a "correctness" test.
NUM_REQUESTS = 20
NUM_THREADS = 20

# Generous wait period (in seconds). This one is longer because we have to wait for two
# WF Instances to complete, and they're separated by a Kafka transport.
WAIT_PERIOD = 10

BPMN_FILE_A = 'data/test7_a.bpmn'
BPMN_FILE_B = 'data/test7_b.bpmn'


class Test7(IntegrationTest):
    def __init__(self):
        self._name = "test7_start_stop_events"
        self._status = TestStatus('not_set_up')
        self._wf_id_a = "test7-a"
        self._wf_id_b = "test7-b"

    def setup(self) -> SetupResult:
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
        test_results = None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            launch_futures = executor.map(lambda _: self.launch_test(), range(NUM_REQUESTS))
            instances = [item for item in launch_futures]
            time.sleep(WAIT_PERIOD)
            test_result_futures = executor.map(self.check_result, instances)
            test_results = [item for item in test_result_futures]

        self._status.set_state('completed')
        return test_results

    def launch_test(self):
        run_response = None
        magic_cookie = uuid.uuid4().hex
        data_arg = '{"magic_cookie": "' + magic_cookie + '"}'
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', data_arg,
                "http://localhost:80/start-test7-a-f2d732d5",
            ], stderr=devnull)
        return json.loads(run_response.decode())['id']

    def check_result(self, instance_id):
        # Check the first instance
        instance = flowctl(f"ps {instance_id} -o")[instance_id]
        if instance['state'] != 'COMPLETED':
            return TestResult(
                [instance_id],
                -1,
                f"Instance didn't complete: {instance}.",
                self._name,
            )

        result_json = json.loads(instance['result'])
        if 'magic_cookie' not in result_json or result_json['sauce'] != 'Applied.':
            return TestResult(
                [instance_id],
                -1,
                f"Bad instance result: {instance}.",
                self._name,
            )
        magic_cookie = result_json['magic_cookie']

        # Find the WF Instance from test7-b that has the same magic cookie
        all_instances = flowctl("ps -o")
        for instance_id_b in all_instances.keys():
            instance_b = all_instances[instance_id_b]
            if instance_b['parent'] != self._wf_id_b:
                continue

            result_json = json.loads(instance_b['result'])
            if result_json['magic_cookie'] == magic_cookie:
                # we found it!
                if result_json['cashflow'] == 'Positive!':
                    return TestResult([instance_id, instance_id_b], 0, "Ok.", "Start-Stop-Event")
                else:
                    return TestResult(
                        [instance_id, instance_id_b],
                        -1,
                        f"Bad result didn't match: {instance_id_b}, {instance_b}",
                        "Start-Stop-Event",
                    )

        return TestResult(
            [instance_id],
            -1,
            f"Didn't find a corresponding instance in WF b. {instance}",
            "Heterogeneous WF."
        )

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id_a) and cleanup_wf_deployment(self._wf_id_b):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id_a, self._wf_id_b], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id_a, self._wf_id_b], -1, "Failed to clean up WF's.")

    def status(self) -> TestStatus:
        return self.status
