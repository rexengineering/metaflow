'''Defines an abstract wrapper for asynchronous service applications.
'''
import logging
from typing import Callable

import requests

from quart import request

from flowlib.config import *
from flowlib.constants import Headers, flow_result
from flowlib.etcd_utils import get_etcd
from flowlib.executor import get_executor
from flowlib.quart_app import QuartApp


class AsyncService(QuartApp):
    def __init__(self, name=__name__, executor=None, **kws):
        super().__init__(name, **kws)
        if executor is None:
            executor = get_executor()
        self.etcd = get_etcd()
        self.app.route('/', methods=['POST'])(self.root_route)
        self.executor = executor

    def root_route(self):
        global request
        ok = self.validate_request(request)
        if not ok:
            # TODO: Add details to result.
            return flow_result(-1, 'Bad request')
        else:
            self.executor.submit(self.handle_request, request)
        return flow_result(0, 'Ok')

    def handle_request(self, local_request):
        # callback is URI of next task in workflow, for example, "Profit!"
        callback = self.get_callback(local_request)
        result = self.actual_handler(local_request)
        callback(result)

    def validate_request(self, local_request):
        raise NotImplementedError('Overload me!')

    def get_instance_etcd_key(self, local_request) -> str:
        wf_instance = local_request.headers[Headers.FLOWID_HEADER]
        task_id = getattr(self.config, 'task_id', local_request.headers[Headers.X_HEADER_WORKFLOW_ID])
        # TODO: Move this format string to constants.  Add support for
        # populating this key at workflow run time.
        return f'/rexflow/instances/{wf_instance}/user_tasks/{task_id}/'

    # TODO: Consider moving this (or something similar) to a convenience method
    # or function at a higher level of abstraction (like Colt's etcd wrapper idea).
    def get_etcd_value(self, local_request, key: str) -> str:
        return self.etcd.get(f'{self.get_instance_etcd_key(local_request)}{key}')[0].decode()

    def get_callback(self, local_request) -> Callable:
        def _default_callback(data):
            try:
                response_endpoint = self.get_etcd_value(local_request, 'response_url')
                response = requests.post(response_endpoint, data)
                if not response.ok:
                    logging.error(response)
            except Exception as exn:
                logging.exception(exn)
        return _default_callback

    def actual_handler(self, request):
        raise NotImplementedError('Overload me!')
