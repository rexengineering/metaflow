from quart import request, jsonify
import json
import logging
import os
import requests
from urllib.parse import urlparse

from flowlib.quart_app import QuartApp
from flowlib.constants import (
    Headers,
    flow_result,
)
from flowlib.config import XGW_LISTEN_PORT


CONDITIONAL_PATHS = json.loads(os.environ['REXFLOW_XGW_CONDITIONAL_PATHS'])
DEFAULT_PATH = json.loads(os.environ['REXFLOW_XGW_DEFAULT_PATH'])
REXFLOW_XGW_FAIL_URL = os.environ['REXFLOW_XGW_FAIL_URL']
KAFKA_SHADOW_URL = os.getenv("REXFLOW_KAFKA_SHADOW_URL", None)


FORWARD_HEADERS = [
    'x-request-id',
    'x-b3-traceid',
    'x-b3-spanid',
    'x-b3-parentspanid',
    'x-b3-sampled',
    'x-b3-flags',
    'x-ot-span-context',
]

DMN_SERVER_HOST = os.getenv("DMN_SERVER_HOST", "http://dmnserver.rexflow:8001")


class ExclusiveGatewayApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.exclusive_gateway)

    def health_check(self):
        return flow_result(0, "Ok.")

    async def exclusive_gateway(self):
        req_json = await request.get_json()
        total_attempts = None
        target_url = None
        target_component_id = None

        # For now, the following loop just iterates over one item (since we haven't yet
        # worked with Jon to figure out how to support multiple outgoing branches in
        # a single XGW).
        for path in CONDITIONAL_PATHS:
            if path['type'] == 'python':
                if eval(path['expression']):
                    total_attempts = path['total_attempts']
                    target_url = path['k8s_url']
                    target_component_id = path['component_id']
                    break
            elif path['type'] == 'feel':
                headers = {Headers.CONTENT_TYPE: 'application/json'}
                dataz = [{path['expression'] : "True", "":"False"}, req_json]

                # TODO: move this hardcoded uri to somwhere configurations live
                response = requests.post(
                    f"{DMN_SERVER_HOST}/dmn/dt",
                    headers=headers,
                    data=json.dumps(dataz)
                )

                if response.json()[0]['result'] == "True":
                    total_attempts = path['total_attempts']
                    target_url = path['k8s_url']
                    target_component_id = path['component_id']
                    break
            else:
                assert False, "unsupported expression type."

        if not target_url and not total_attempts and not target_component_id:
            total_attempts = DEFAULT_PATH['total_attempts']
            target_url = DEFAULT_PATH['k8s_url']
            target_component_id = DEFAULT_PATH['component_id']

        headers = {
            Headers.X_HEADER_FLOW_ID: request.headers[Headers.X_HEADER_FLOW_ID.lower()],
            Headers.X_HEADER_WORKFLOW_ID: request.headers[Headers.X_HEADER_WORKFLOW_ID.lower()],
            Headers.X_HEADER_TASK_ID: target_component_id,
        }
        for h in FORWARD_HEADERS:
            if h in request.headers:
                headers[h] = request.headers[h]

        success = False
        for _ in range(int(total_attempts)):
            try:
                response = requests.post(target_url, json=req_json, headers=headers)
                response.raise_for_status()
                success = True
                break
            except Exception:
                logging.error(
                    f"failed making a call to {target_url} on wf {request.headers['x-rexflow-iid']}"
                )

        o = urlparse(target_url)
        headers[Headers.X_HEADER_ORIGINAL_HOST] = o.netloc
        headers[Headers.X_HEADER_ORIGINAL_PATH] = o.path

        if not success:
            # Notify Flowd that we failed.
            requests.post(REXFLOW_XGW_FAIL_URL, json=req_json, headers=headers)

        if KAFKA_SHADOW_URL:
            try:
                headers['x-rexflow-failure'] = True
                requests.post(KAFKA_SHADOW_URL, headers=headers, json=req_json).raise_for_status()
            except Exception:
                logging.warning("Failed shadowing traffic to Kafka")

        resp = jsonify({"status": 200, "msg": ""})
        if Headers.TRACEID_HEADER.lower() in request.headers:
            resp.headers[Headers.TRACEID_HEADER] = request.headers[Headers.TRACEID_HEADER]
        return resp


if __name__ == '__main__':
    app = ExclusiveGatewayApp(bind=f'0.0.0.0:{XGW_LISTEN_PORT}')
    app.run()
