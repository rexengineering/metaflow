import argparse
import json
import logging
import os
import time

from util import (
    cleanup_wf_deployment,
    flowctl,
    wait_for_status,
    test_result,
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


def test1():
    '''
    Verifies simple WF functionality. Deploys a one-step WF to the default namespace.
    '''
    # Safety check to ensure we don't accidentally pollute a production cluster.
    # Not that anyone here's done that before 😏
    os.system("kubectl config use-context docker-desktop")

    # Step 1: apply Istio Underpants
    out = flowctl("apply ../../examples/istio/istio-underpants.bpmn -o")
    wf_id = out['wf_id']

    # Step 2: wait for deployment to come up
    if not wait_for_status(wf_id, 'RUNNING'):
        return test_result([wf_id], [], -1, "WF Deployment failed to come up.")

    # Step 3: Run an instance
    run_response = flowctl("run " + wf_id + " '{}' -o")
    instance_id = run_response['id']

    # Step 4: Wait for instance to complete. It should be fast.
    time.sleep(1)
    ps_response = flowctl(f"ps {instance_id} -o")
    instance = ps_response[instance_id]

    # Step 5: Interrogate the Instance Output
    result_json = json.loads(instance['result'])

    if instance['state'] != 'COMPLETED':
        return test_result([wf_id], [instance_id], -1, "Instance didn't complete.")

    if result_json not in [EXPECTED, EXPECTED_2]:
        return test_result([wf_id], [instance_id], -1, "Result didn't match.")

    return test_result([wf_id], [instance_id], 0, "Ok.")


ALL_TESTS = [
    test1,
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Underpants Test')
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help="Don't cleanup deployment after running",
    )
    ns = parser.parse_args()
    should_cleanup = not ns.no_cleanup

    results = [
        test() for test in ALL_TESTS
    ]

    wf_ids = []
    for result in results:
        wf_ids.extend(result['wf_ids'])
    all_ok = all([result['status'] == 0 for result in results])

    if should_cleanup:
        for wf_id in wf_ids:
            cleanup_wf_deployment(wf_id)

    if not all_ok:
        logging.error("Tests didn't pass.")
        exit(1)
    