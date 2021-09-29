from concurrent.futures import ThreadPoolExecutor
import multiprocessing


# High number of workers because we use this for i/o bound tasks.
# Specifically in healthd, most of the time is spent sleeping rather
# than doing anything. See REXFLOW-209.
MIN_WORKERS = 32


def _init_get_executor():
    executor = None

    def _get_executor():
        nonlocal executor
        max_workers = max(multiprocessing.cpu_count(), MIN_WORKERS)
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers)
        return executor
    return _get_executor


get_executor = _init_get_executor()
