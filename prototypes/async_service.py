'''Defines an abstract wrapper for asynchronous service applications.
'''
import logging

import requests

from quart import request

from flowlib.etcd_utils import get_etcd
from flowlib.quart_app import QuartApp


class AsyncService(QuartApp):
    def __init__(self, executor, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=['POST'])(self.root_route)
        self.executor = executor

    def root_route(self):
        ok = self.validate_request(request)
        if not ok:
            return ValueError("invalid input")
        else:
            self.executor.submit(self.handle_request(request))
        return "ok"

    def handle_request(self, request):
        # callback is URI of next task in workflow, for example, "Profit!"
        callback = self.get_callback(request)
        result = self.actual_handler(request)
        callback(result)

    def validate_request(self, request):
        raise NotImplementedError('Overload me!')

    def get_callback(self, request):
        def _default_callback(data):
            try:
                response = requests.post('http://asynchandler/', data)
                if not response.ok:
                    logging.error(response)
            except Exception as exn:
                logging.exception(exn)
        return _default_callback

    def actual_handler(self, request):
        raise NotImplementedError('Overload me!')
