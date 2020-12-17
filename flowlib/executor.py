from concurrent.futures import ThreadPoolExecutor
import multiprocessing


def _init_get_executor():
    executor = None

    def _get_executor():
        nonlocal executor
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        return executor
    return _get_executor


get_executor = _init_get_executor()
