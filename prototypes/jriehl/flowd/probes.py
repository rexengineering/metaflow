from concurrent.futures import ThreadPoolExecutor
import logging
import multiprocessing
import time

from etcd3.events import PutEvent, DeleteEvent

from flowlib.etcd_utils import get_etcd, transition_state


def _init_get_executor():
    executor = None
    def _get_executor():
        nonlocal executor
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 2)
        return executor
    return _get_executor

get_executor = _init_get_executor()


probes = {}


def add_health_probe(workflow_id):
    etcd = get_etcd()
    def do_health_check():
        # FIXME: Make this a valid health probe.
        logging.info(f'Running bogus health probe for {workflow_id}.')
        watch_key = f'/prototype/{workflow_id}'
        state_key = f'/rexflow/workflows/{workflow_id}/state'
        watch_iter, _ = etcd.watch(watch_key)
        watch_key_bytes = watch_key.encode('utf-8')
        for event in watch_iter: # Should run forever.
            logging.info(f'Got health event {event}')
            assert event.key == watch_key_bytes
            if isinstance(event, PutEvent):
                if event.value == b'HEALTHY':
                    # Originally thought transactions were the way to go, but
                    # they lack support for checking that a value is one of a set
                    # of values.
                    transition_state(etcd, state_key, (b'STARTING', b'ERROR'), b'RUNNING')
                elif event.value == b'UNHEALTHY':
                    transition_state(etcd, state_key, (b'STARTING', b'RUNNING'), b'ERROR')
            elif isinstance(event, DeleteEvent):
                break # Well, run forever until the bogus probe key is removed. 
        return 0
    return get_executor().submit(do_health_check)
