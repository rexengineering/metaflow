import argparse
import json
import os
import time

from utils.util import (
    flowctl,
    wait_for_status,
)


EXPECTED = {
    "cashflow": "Positive!",
    "sauce": "Applied.",
    "underpants": "Not collected ):"
}

EXPECTED_2 = {
    "cashflow": "Positive!",
    "sauce": "Applied.",
    "underpants": "Collected.",
}


def run_test(cleanup):
    # Safety check to ensure we don't accidentally pollute a production cluster.
    # Not that anyone here's done that before 😏
    os.system("kubectl config use-context docker-desktop")

    # Step 1: apply Istio Underpants
    out = flowctl("apply ../../examples/istio/istio-underpants.bpmn -o")
    wf_id = out['wf_id']

    # Step 2: wait for deployment to come up
    assert wait_for_status(wf_id, 'RUNNING'), "Deployment failed to come up"

    # Step 3: Run an instance
    run_response = flowctl("run " + wf_id + " '{}' -o")
    instance_id = run_response['id']

    # Step 4: Wait for instance to complete. It should be fast.
    time.sleep(1)
    ps_response = flowctl(f"ps {instance_id} -o")
    instance = ps_response[instance_id]

    # Step 5: Interrogate the Instance Output
    result_json = json.loads(instance['result'])

    assert instance['state'] == 'COMPLETED'
    assert result_json == EXPECTED or result_json == EXPECTED_2

    if cleanup:
        print("Cleaning up deployment...")
        flowctl(f"stop -k DEPLOYMENT {wf_id}")

        # Takes a long time for deployment to come down.
        assert wait_for_status(wf_id, "STOPPED", timeout_seconds=180), f"Failed to stop {wf_id}"

        flowctl(f"delete -k DEPLOYMENT {wf_id}")

        # Make sure deployment is gone
        time.sleep(3)
        response = flowctl(f"ps -k DEPLOYMENT {wf_id} -o")
        assert response[wf_id] == {}, "WF Should have been deleted by now."

    print("SUCCESS!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Underpants Test')
    parser.add_argument(
        '--no-cleanup',
        action='store_false',
        help="Don't cleanup deployment after running",
    )
    ns = parser.parse_args()
    run_test(ns.no_cleanup)
