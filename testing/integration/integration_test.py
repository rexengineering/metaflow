import argparse
import logging
import os

from test1 import Test1


ALL_TESTS = [
    Test1
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
    failure = False
    test_objects = [
        factory() for factory in ALL_TESTS
    ]

    # Safety check to ensure we don't accidentally pollute a production cluster.
    # Not that anyone here's done that before 😏
    os.system("kubectl config use-context docker-desktop")

    for test_object in test_objects:
        # setup
        sr = test_object.setup()
        if sr.status != 0:
            logging.error(f"Setup FAILED on test {test_object.name}: {sr.message}")
            failure = True
            continue

        # Run
        trs = test_object.run()
        for tr in trs:
            if tr.status != 0:
                logging.error(
                    f"{test_object.name} FAILED on {tr.name}: {tr.message}"
                )
                logging.error(
                    f"Instance ID: {tr.instance_ids}"
                )
                failure = True

        # cleanup
        cr = test_object.cleanup()
        if cr.status != 0:
            logging.error(f"{test_object.name} FAILED to cleanup: {cr.message}")

    if failure:
        logging.error("Tests didn't pass.")
        exit(1)

    print("SUCCESS!", flush=True)
