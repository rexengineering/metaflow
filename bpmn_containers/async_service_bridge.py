"""
Bridge between an asynchronous worker service and a REXFlow workflow.
"""
from flowlib.config import INSTANCE_FAIL_ENDPOINT
from flowlib import workflow
import logging
import json
import os
import requests
from typing import List, Mapping

from quart import request, jsonify, Response
from quart_cors import cors

from flowlib.config import INSTANCE_FAIL_ENDPOINT
from flowlib.constants import (
    flow_result,
    WorkflowInstanceKeys,
    Headers,
    generate_request_id,
    ErrorCodes,
    split_key,
)
from flowlib.etcd_utils import get_etcd
from flowlib.flowpost import FlowPost, FlowPostStatus
from flowlib.quart_app import QuartApp


def sanitize_headers(headers):
    out = headers.copy()
    if 'host' in out:
        del out['host']
    if 'Host' in out:
        del out['Host']
    return out

class EventCatchApp(QuartApp):
    def __init__(
        self,
        task_url=None,
        use_closure_transport=None,
        task_id=None,
        wf_id=None,
        host=None,
        forward_tasks=None,
        context_params=None,
        **kws
    ):
        super().__init__(__name__, **kws)
        self.app = cors(self.app)
        self._etcd = get_etcd()

        self._task_url = task_url or os.environ["ASYNC_TASK_URL"]
        logging.info(f"Configured to post to {self._task_url}")

        self._task_id = task_id or os.environ["ASYNC_TASK_ID"]

        self._use_closure_transport = bool(use_closure_transport) or \
            (os.getenv("CLOSURE_TRANSPORT", "false").lower() == 'true')

        self.wf_id = wf_id or os.environ['WF_ID']

        self.host = host or os.environ['ASYNC_BRIDGE_HOST']

        if forward_tasks is None:
            forward_tasks = json.loads(os.environ['ASYNC_BRIDGE_FORWARD_TASKS'])

        self._forward_tasks = forward_tasks # type: List[Mapping[str, str]]
        logging.info(f"Forward tasks are: {self._forward_tasks}")

        self._context_params = []
        if self._use_closure_transport:
            self._context_params = context_params or json.loads(
                os.environ['ASYNC_BRIDGE_CONTEXT_PARAMETERS']
            )

        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.start_work)
        self.app.route('/<instance_id>/<task_id>/<request_id>', methods=['POST'])(self.callback)

    def health_check(self):
        return jsonify(flow_result(0, "Ok."))

    async def start_work(self):
        headers = sanitize_headers(request.headers)
        instance_id = headers[Headers.X_HEADER_FLOW_ID]
        task_id = headers[Headers.X_HEADER_TASK_ID]
        assert task_id == self._task_id
        data = await request.data
        try:
            incoming_json = json.loads(data.decode())
        except Exception as exn:
            self._raise_context_input_error(
                instance_id,
                task_id,
                data,
                headers,
                f"Failed loading input json: {exn}",
            )
            logging.exception(
                f"Instance {instance_id} failed parsing input data",
                exc_info=exn,
            )
            return jsonify(flow_result(-1, "Bad json input provided."))

        # Log to etcd that we've started work.
        request_id = generate_request_id()
        etcd_key = WorkflowInstanceKeys.async_request_payload_key(
            instance_id, task_id, request_id
        )
        self._etcd.put(etcd_key, json.dumps(incoming_json))
        # Initialize the key so that we can .replace() it later on.
        self._etcd.put(WorkflowInstanceKeys.async_callback_response_key(
            instance_id, task_id, request_id
        ), b'')

        if self._use_closure_transport:
            payload = {}
            for param in self._context_params['input_params']:
                if not param['has_default_value'] and param['value'] not in incoming_json:
                    self._raise_context_input_error(
                        instance_id,
                        task_id,
                        data,
                        request.headers,
                        f"Could not find param {param['value']} in request input data.",
                    )
                    # Return a 200 response because we already did error handling.
                    return jsonify(flow_result(-1, "context input parse failure."))

                payload[param['name']] = incoming_json.get(
                    param['value'], param['default_value']
                )

        else:
            payload = incoming_json

        logging.info(
            f"Making request id {request_id} to {self._task_url}."
        )
        payload['callback_url'] = f'{self.host}{instance_id}/{self._task_id}/{request_id}'

        poster = FlowPost(
            instance_id,
            task_id,
            json.dumps(payload),
            headers=headers,
            url=self._task_url,
        )
        result = poster.send()
        logging.info(f"{request_id} got response {result.response}.")

        if result.message == FlowPostStatus.SUCCESS:
            code = 0
            message = "Successfully started work."
        else:
            code = -1
            message = "Failed to start work. We have notified flowd."
        return jsonify(flow_result(code, message))

    async def callback(self, instance_id, task_id, request_id):
        logging.info(
            f"Started callback work on instance {instance_id} task {task_id} {request_id}."
        )
        payload_key = WorkflowInstanceKeys.async_request_payload_key(
            instance_id, task_id, request_id
        )
        payload = json.loads(self._etcd.get(payload_key)[0].decode()) # type: dict
        logging.info(f"Got payload from before Async Request: {payload}")
        incoming_data = await request.data

        callback_response_key = WorkflowInstanceKeys.async_callback_response_key(
            instance_id, task_id, request_id
        )

        if not self._etcd.replace(callback_response_key, b'', incoming_data):
            logging.error(
                f"Instance {instance_id} Task {task_id} request {request_id} already"
                " got called back on the Async Bridge callback!"
            )
            self._report_too_many_callbacks_failure(
                instance_id,
                task_id,
                request_id,
                payload,
                incoming_data,
                dict(request.headers),
            )
            return jsonify(flow_result(-1, "Error! Already called us back."), 400)

        try:
            incoming_json = json.loads(incoming_data.decode()) # type: dict
            if self._use_closure_transport:
                updater = {}
                for param in self._context_params['output_params']:
                    if not param['has_default_value'] and param['value'] not in incoming_json:
                        raise ValueError(
                            f"Could not find parameter f{param['name']} in async callback data."
                        )
                    updater[param['name']] = incoming_json.get(
                        param['value'], param['default_value']
                    )
            else:
                updater = incoming_json
            # TODO: process bavs parameters.
        except Exception as exn:
            logging.warning(
                f"Failed parsing callback response on instance {instance_id}"
                f" task {task_id} request {request_id}"
            )
            self._raise_context_output_error(
                instance_id,
                task_id,
                request_id,
                payload,
                incoming_data,
                dict(request.headers),
                message=str(exn),
            )
            raise exn from None

        payload.update(updater)

        for forward_task in self._forward_tasks:
            url = forward_task['k8s_url']
            next_task_id = forward_task['task_id']
            method = forward_task['method']
            total_attempts = forward_task['total_attempts']
            poster = FlowPost(
                instance_id=instance_id,
                task_id=next_task_id,
                data=json.dumps(payload),
                headers={"content-type": "application/json"},
                url=url,
                method=method,
                retries=total_attempts - 1,
            )
            result = poster.send()
            if result.message != FlowPostStatus.SUCCESS:
                logging.warning(
                    f"Failed making call to {task_id}."
                )

        return jsonify(flow_result(0, "Ok."))

    # TODO: This should be moved to the flowlib.workflow.WorkflowInstance class. See
    # the REXFLOW-210 ticket.
    def _raise_context_output_error(
        self,
        instance_id: str,
        task_id: str,
        request_id: str,
        original_data: dict,
        callback_data: bytes,
        callback_headers: Mapping[str, str],
        message: str = "Failed parsing callback response.",
    ):
        """Moves the Workflow Instance to the ERROR state because we were unable to
        parse the info sent to us by the Asynchronous Service on our callback.
        """
        payload = {
            'output_data': FlowPost.jsonify_or_encode_data(callback_data),
            'output_headers': dict(callback_headers),
            'input_data': original_data,
            'error_code': ErrorCodes.FAILED_TASK,
            'error_msg': message + " on request id" + request_id,
            'from_envoy': False,
        }
        workflow_id, _ = split_key(instance_id)
        headers = {
            Headers.X_HEADER_FLOW_ID: instance_id,
            Headers.X_HEADER_TASK_ID: task_id,
            Headers.X_HEADER_WORKFLOW_ID: workflow_id,
            Headers.CONTENT_TYPE: "application/json",
        }
        requests.post(
            INSTANCE_FAIL_ENDPOINT,
            data=json.dumps(payload),
            headers=headers,
        )

    # TODO: This should be moved to the flowlib.workflow.WorkflowInstance class. See
    # the REXFLOW-210 ticket.
    def _report_too_many_callbacks_failure(
        self,
        instance_id: str,
        task_id: str,
        request_id: str,
        original_data: dict,
        callback_data: bytes,
        callback_headers: Mapping[str, str],
    ):
        """Report an instance-level failure when the Async Service calls back
        the Async Service Bridge more than one time on the same request.
        """
        msg = f'Received more than one callback for async task {task_id} req {request_id}.'
        payload = {
            'output_data': FlowPost.jsonify_or_encode_data(callback_data),
            'output_headers': dict(callback_headers),
            'input_data': original_data,
            'error_code': ErrorCodes.FAILED_TASK,
            'error_msg': msg,
            'from_envoy': False,
        }
        workflow_id, _ = split_key(instance_id)
        headers = {
            Headers.X_HEADER_FLOW_ID: instance_id,
            Headers.X_HEADER_TASK_ID: task_id,
            Headers.X_HEADER_WORKFLOW_ID: workflow_id,
            Headers.CONTENT_TYPE: "application/json",
        }
        requests.post(
            INSTANCE_FAIL_ENDPOINT,
            data=json.dumps(payload),
            headers=headers,
        )

    # TODO: This should be moved to the flowlib.workflow.WorkflowInstance class. See
    # the REXFLOW-210 ticket.
    def _raise_context_input_error(self, instance_id, task_id, input_data, input_headers, msg):
        """Called when input to the service bridge was not what we expected.
        """
        payload = {
            'input_data': FlowPost.jsonify_or_encode_data(input_data),
            'input_headers': dict(input_headers),
            'error_code': ErrorCodes.FAILED_CONTEXT_INPUT_PARSING,
            'error_msg': msg,
            'from_envoy': False,
        }
        workflow_id, _ = split_key(instance_id)
        headers = {
            Headers.X_HEADER_FLOW_ID: instance_id,
            Headers.X_HEADER_TASK_ID: task_id,
            Headers.X_HEADER_WORKFLOW_ID: workflow_id,
            Headers.CONTENT_TYPE: "application/json",
        }
        requests.post(
            INSTANCE_FAIL_ENDPOINT,
            data=json.dumps(payload),
            headers=headers,
        )

    def _shutdown(self):
        pass


if __name__ == '__main__':
    app = EventCatchApp(bind=f'0.0.0.0:5000')
    app.run()
