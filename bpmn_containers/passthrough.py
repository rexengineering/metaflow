'''
This file runs as a daemon in the background. It constantly polls a kinesis
stream for events that are published into the WF instance and calls the next
step in the workflow with that data.
'''
import json
import os
import requests

from quart import request, jsonify, Response
from quart_cors import cors

from flowlib.executor import get_executor
from flowlib.quart_app import QuartApp
from flowlib.constants import (
    Headers,
    flow_result,
)


CONFIG = json.loads(os.environ['REXFLOW_PASSTHROUGH_CONFIG'])
LISTEN_PORT = CONFIG['target_port']


class PassthroughApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.executor = get_executor()
        self.app = cors(self.app)

        self.app.route('/', methods=['GET'])(self.health_check)
        self.target_url_base = CONFIG['target_url']

        self.handlers = {
            'POST': self.post,
            'GET': self.get,
            'PATCH': self.patch,
            'PUT': self.put,
            'DELETE': self.delete,
        }

        endpoints = [(target['path'], target['method']) for target in CONFIG['targets']]
        already_routed = []
        for path, method in endpoints:
            if f'{path}.{method}' not in already_routed:
                handler = self.handlers[method]
                already_routed.append(f'{path}.{method}')
                self.app.route(path, methods=[method])(handler)

    def health_check(self):
        return jsonify(flow_result(0, ""))

    async def post(self):
        result = await self.passthrough(requests.post)
        return result
    
    async def get(self):
        result = self.passthrough(requests.get)
        return result

    async def patch(self):
        result = self.passthrough(requests.patch)
        return result

    async def delete(self):
        result = self.passthrough(requests.delete)
        return result

    async def put(self):
        result = self.passthrough(requests.put)
        return result

    async def passthrough(self, call_method):
        data = await request.data
        headers = dict(request.headers)
        # Necessary so we don't accidentally run a workflow up there
        if Headers.X_HEADER_FLOW_ID in headers:
            del headers[Headers.X_HEADER_FLOW_ID]

        # Necessary so we don't confuse the Istio-Ingressgateway
        if 'Host' in headers:
            del headers['Host']

        target_url = f'{self.target_url_base}{request.path}'
        passthrough_response = call_method(
            target_url, data=data, headers=headers
        )
        return Response(
            passthrough_response.content,
            status=passthrough_response.status_code,
            headers=headers,
        )

    def _shutdown(self):
        pass

    def run(self):
        # bring up the web server (this call blocks)
        super().run()


if __name__ == '__main__':
    app = PassthroughApp(bind=f'0.0.0.0:{LISTEN_PORT}')
    app.run_serve()
