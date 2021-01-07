from concurrent.futures import ThreadPoolExecutor
import multiprocessing


MIN_WORKERS = 2

def _init_get_executor():
    executor = None

    def _get_executor():
        nonlocal executor
        max_workers = min(multiprocessing.cpu_count(), MIN_WORKERS)
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers)
        return executor
    return _get_executor


get_executor = _init_get_executor()
