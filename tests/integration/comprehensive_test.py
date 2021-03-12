'''This file runs a test to verify that we can:
1. Throw an event to kafka upon workflow completion
2. Start a WF Instance by listening to Kafka.
'''
from concurrent.futures import ThreadPoolExecutor
import json
import logging
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
NUM_REQUESTS = 200
NUM_THREADS = 20

# The instances should take a while to complete because the kafka util runs slowly.
WAIT_PERIOD = 40

BPMN_FILE_A = 'data/comprehensive_test.bpmn'
BPMN_FILE_B = 'data/comprehensive_test_b.bpmn'
YAML_FILE = 'data/comprehensive_test_increment.yaml'


class ComprehensiveTest(IntegrationTest):
    def __init__(self):
        self._name = "comprehensive_test"
        self._status = TestStatus('not_set_up')
        self._wf_id_a = None
        self._wf_id_b = None

    def setup(self) -> SetupResult:
        os.system(f"./inject_and_deploy.sh {YAML_FILE}")
        result = None
        self._wf_id_a = flowctl(f"apply {BPMN_FILE_A} -o")['wf_id']
        self._wf_id_b = flowctl(f"apply {BPMN_FILE_B} -o")['wf_id']
        wf_ids = [self._wf_id_a, self._wf_id_b]

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
        instance_futures = None
        result_futures = None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            instance_futures = executor.map(self.launch_instance, range(-50, NUM_REQUESTS - 50))

        self.run_kafka_util()
        instances = [item for item in instance_futures]
        time.sleep(WAIT_PERIOD)

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            result_futures = executor.map(self.wait_for_instance, instances)

        test_results = [r for r in result_futures]
        self._status.set_state('completed')
        return test_results

    def launch_instance(self, value):
        run_response = None
        magic_cookie = uuid.uuid4().hex
        data_arg = '{"val": ' + str(value) + ', "magic_cookie": "' + magic_cookie + '"}'
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', data_arg,
                f"http://localhost:80/start-{self._wf_id_a}",
            ], stderr=devnull)
        return json.loads(run_response.decode())['id'], value, magic_cookie

    def compute_output(self, input_val):
        return (((input_val + 2) * 2) - 1) * 2

    def wait_for_instance(self, instance_tuple) -> TestResult:
        instance_id, val, magic_cookie = instance_tuple
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        result = json.loads(instance['result'])
        if val < 0:
            success, secondary_id = self.check_for_secondary_wf_instance(magic_cookie, val)
            if not success:
                return TestResult(
                    [instance_id, secondary_id],
                    -1,
                    "Didn't raise event that spawns successful WF Instance.",
                    self._name,
                )
            expected = {"val": val + 1, "magic_cookie": magic_cookie}
            if result != expected:
                return TestResult(
                    [instance_id, secondary_id],
                    -1,
                    f"Result didn't match: {result} != {expected}",
                    self._name,
                )
            # all good!
            return TestResult([instance_id, secondary_id], 0, "Ok.", self._name,)

        elif self.compute_output(val) < 100:
            if result['val'] == self.compute_output(val) and result['sauce'] == 'Applied.':
                return TestResult([instance_id], 0, "Ok.", f"comprehensive test {val}")
            else:
                return TestResult([instance_id], -1, "Result didn't match.", self._name)

        else:
            if result['val'] == self.compute_output(val) and result['cashflow'] == 'Positive!':
                return TestResult([instance_id], 0, "Ok.", f"comprehensive test {val}")
            else:
                return TestResult([instance_id], -1, "Result didn't match.", self._name)

    def check_for_secondary_wf_instance(self, magic_cookie, val):
        # Find the WF Instance from comprehensive-test-negative-balance that has the same cookie
        all_instances = flowctl("ps -o")
        for instance_id_b in all_instances.keys():
            instance_b = all_instances[instance_id_b]
            if instance_b['parent'] != self._wf_id_b:
                continue

            result_json = json.loads(instance_b['result'])
            if result_json['magic_cookie'] == magic_cookie:
                # we found it!
                return (result_json['cashflow'] == 'Orz', instance_id_b)

        return False, None

    def run_kafka_util(self):
        # Run the kafka util. Recall that this simulates a BPMN Role from a different BPMN SwimLane
        # than the backend microservices (i.e. REXFlow) lane. For example, at REX, this might
        # be a customer replying to an email, etc.
        pods = str(check_output("kubectl get po -ndefault".split())).split('\\n')
        increment_pods = [p for p in pods if 'increment-test' in p and 'Running' in p]
        increment_pod = increment_pods[0].split()[0]

        kafka_poller_response = check_output(
            f"kubectl exec -ndefault {increment_pod} -- python ./comprehensive_test_kafka_util.py"
            .split()
        )
        logging.info(kafka_poller_response.decode())

    def cleanup(self) -> CleanupResult:
        os.system(f"kubectl delete -f {YAML_FILE}")
        if cleanup_wf_deployment(self._wf_id_a) and cleanup_wf_deployment(self._wf_id_b):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id_a, self._wf_id_b], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id_a, self._wf_id_b], -1, "Failed to clean up WF's.")

    def status(self) -> TestStatus:
        return self.status
