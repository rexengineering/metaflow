import argparse
import logging
import os

from comprehensive_test import ComprehensiveTest
from test1 import Test1
from test2 import Test2
from test3 import Test3
from test4 import Test4
from test5 import Test5
from test6 import Test6
from test7 import Test7


logging.getLogger().setLevel(logging.INFO)

ALL_TESTS = [
    Test1,
    Test2,
    Test3,
    Test4,
    Test5,
    Test6,
    Test7,
]

if __name__ == "__main__":
    failure = False
    parser = argparse.ArgumentParser(description='Run Underpants Test')
    parser.add_argument(
        '--all-tests',
        action='store_true',
        help="Run all individual tests, not just the comprehensive one.",
    )
    ns = parser.parse_args()
    test_objects = [factory() for factory in ALL_TESTS] if ns.all_tests else []
    test_objects.append(ComprehensiveTest())

    # Safety check to ensure we don't accidentally pollute a production cluster.
    # Not that anyone here's done that before 😏
    os.system("kubectl config use-context docker-desktop")

    for test_object in test_objects:
        # setup
        logging.info(f"Setting up deployment for test {test_object.name}.")
        sr = test_object.setup()
        if sr.status != 0:
            logging.error(f"Setup FAILED on test {test_object.name}: {sr.message}")
            failure = True
            continue
        logging.info(f"Successfully set up deployment for {test_object.name}.")

        # Run
        logging.info(f"Running all test cases for test deployment {test_object.name}.")
        trs = test_object.run()
        for tr in trs:
            if tr.status != 0:
                logging.error(
                    f"{test_object.name} FAILED on {tr.name}: {tr.message}"
                )
                logging.error(
                    f"Instance ID: {tr.instance_ids}"
                )
                exit(1)
        logging.info("Test cases passed.")

        # cleanup
        logging.info(f"Cleaning up deployment {test_object.name}.")
        cr = test_object.cleanup()
        if cr.status != 0:
            logging.error(f"{test_object.name} FAILED to cleanup: {cr.message}")
        logging.info(f"Done cleaning up deployment {test_object.name}.\n\n\n\n")

    if failure:
        logging.error("Tests didn't pass.")
        exit(1)

    print("SUCCESS!", flush=True)
