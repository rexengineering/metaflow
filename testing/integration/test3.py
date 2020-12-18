'''This test simulates interaction between the REXFlow swimlane and another  swimlane using
Kafka Events. See the `data/test3_events.bpmn` file, which contains the spec for the REXFlow
swimlane. The file `test_containers/src/test3_kafka_util.py` simulates an agent from another
swimlane by processing an Event that was thrown, and throwing another Event back into the
REXFlow swimlane.

Anyways, that's enough with academic stuff...in concrete terms, this tests our Kafka Events
code.
'''
from concurrent.futures import ThreadPoolExecutor
import json
import logging
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

BPMN_FILE = 'data/test3_events.bpmn'

# Make sure we can handle high volume in short amount of time
NUM_REQUESTS = 200
NUM_THREADS = 40


class Test3(IntegrationTest):
    def __init__(self):
        self._name = "test3_events"
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
        self._status.set_state('running')
        instance_futures = None
        result_futures = None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            instance_futures = executor.map(self.run_instance, range(NUM_REQUESTS))

        # Run the kafka util. Recall that this simulates a BPMN Role from a different BPMN SwimLane
        # than the backend microservices (i.e. REXFlow) lane. For example, at REX, this might
        # be a customer replying to an email, etc.
        test3_pods = str(check_output("kubectl get po -ntest3".split())).split('\\n')
        increment_pods = [p for p in test3_pods if 'increment-test' in p and 'Running' in p]
        increment_pod = increment_pods[0].split()[0]

        kafka_poller_response = check_output(
            f"kubectl exec -ntest3 {increment_pod} -- python ./test3_kafka_util.py".split()
        )
        logging.info(kafka_poller_response.decode())

        instances = [item for item in instance_futures]

        # Run a bunch of instances
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            result_futures = executor.map(self.wait_for_instance, instances)

        out = [r for r in result_futures]
        self._status.set_state('completed')
        return out

    def run_instance(self, val):
        run_response = None
        with open(os.devnull, 'w') as devnull:
            run_response = check_output([
                'curl', '-H', "content-type: application/json", '-d', '{"val": ' + str(val) + "}",
                "http://localhost:80/start-test3",
            ], stderr=devnull)

        return json.loads(run_response.decode())['id'], val

    def wait_for_instance(self, instance_tuple) -> TestResult:
        instance_id, val = instance_tuple

        # Step 2: Wait for instance to complete. Give a few seconds since the other SwimLane
        # may take a while to do its job.
        time.sleep(12)
        ps_response = flowctl(f"ps {instance_id} -o")
        instance = ps_response[instance_id]

        # Step 3: Interrogate the Instance Output
        if instance['state'] != 'COMPLETED':
            return TestResult([instance_id], -1, "Instance didn't complete.", self._name)

        result_json = json.loads(instance['result'])
        if result_json != {"val": (2 * (val + 1)) - 1}:
            return TestResult([instance_id], -1, "Result didn't match.", self._name)

        return TestResult([instance_id], 0, "Ok.", f"Swimlane Simulation {val}")

    def cleanup(self) -> CleanupResult:
        if cleanup_wf_deployment(self._wf_id):
            self._status.set_state('cleaned_up')
            return CleanupResult([self._wf_id], 0, "Ok.")
        else:
            return CleanupResult([self._wf_id], -1, f"Failed to clean up wf {self._wf_id}.")

    def status(self) -> TestStatus:
        return self.status
