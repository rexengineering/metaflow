"""The goal of this module is to coalesce all of the logic regarding retries,
wf instance ERROR reporting, and traffic shadowing into one place.

As of this commit, the module is just a placeholder and will be fully fleshed
out soon. See REXFLOW-188.
"""
import base64
from enum import Enum
import logging
import json
import requests
from typing import Dict, Mapping, Optional, Union, Callable
from urllib.parse import urlparse

from requests import models
from flowlib import bpmn

from flowlib.config import INSTANCE_FAIL_ENDPOINT
from flowlib.constants import Headers, WorkflowInstanceKeys, split_key, ErrorCodes
from flowlib.bpmn import BPMNComponent
from flowlib.executor import get_executor
from flowlib.workflow import Workflow


CONNECT_TIMEOUT = 3
REQUEST_TIMEOUT = 30
TIMEOUT = (CONNECT_TIMEOUT, REQUEST_TIMEOUT)


class FlowPostStatus(Enum):
    SUCCESS = "SUCCESS"
    REPORTED_ERROR = "REPORTED_ERROR"
    FAILED_TO_REPORT_ERROR = "FAILED_TO_REPORT_ERROR"


class FlowPostResult:
    """Tuple of response and message. The response is the HTTP response of the
    successful request (or last failed request). The message tells us whether:
    * The call succeeded OR
    * The call failed and we successfully reported the Instance-level failure OR
    * The call failed and we did NOT succeed in reporting the Instance-level failure.
    """
    def __init__(self, response: Optional[requests.models.Response], message: FlowPostStatus):
        self._response = response
        self._message = message

    @property
    def response(self) -> Optional[requests.models.Response]:
        return self._response

    @property
    def message(self) -> FlowPostStatus:
        return self._message


class FlowPost:
    def __init__(
        self,
        instance_id: str,
        task_id: str,
        data: Union[bytes, str],
        url: str = None,
        method: str = 'post',
        req_method: Optional[Callable[..., requests.models.Response]] = None,
        headers: Optional[Mapping[str, str]] = None,
        retries: int = None,
        shadow_url: str = None,
        workflow_obj: Workflow = None,
        bpmn_component_obj: BPMNComponent = None,
        force_fail: bool = False,
        force_fail_code: int = 500,
    ):
        """Utility for making calls between one task and another. Lazily calculates
        information as needed. Parameters:

        * instance_id: required.
        * task_id: required. The BPMNComponent.id of the thing we're calling.
        * data: required. What to send. Can be empty.

        * method: optional. Defaults to 'post'. Passing method=None results in flowpost
        looking up the task in the workflow in order to determine the appropriate
        method. This is slow, so it is strongly un-recommended.
        * url: optional, but strongly recommended. Passing url=None results in flowpost
        looking up the url for the task associated with instance_id and task_id. This is
        slow and not recommended.
        * total_attempts: optional. How many times to attempt to make the call. This parameter
        is ignored if the request succeeds. If the request fails, then we need this value.
        As usual, the value can be provided (for performance) or it can be looked up.
        * shadow_url: optional. Some workflows are configured to shadow all traffic to a
        specific URL (normally, this URL is a service that dumps the traffic to a Kafka
        topic). If provided, the traffic is shadowed to this URL after the call.
        If shadow_url is None, we look up the appropriate url (which is slower).
        If shadow_url is '', then flowpost does not attempt to shadow traffic.

        Debugging can be assisted by using the force_fail and force_fail_code parameters.
        When set, any all to send() will fail with the provided force_fail_code (default 500.)
        """
        self._instance_id = instance_id
        self._task_id = task_id
        self._data = data
        self._url = url
        self._method = method
        self._req_method = req_method
        self._headers = dict(headers) if headers else {}
        self._retries = retries
        self._workflow_obj = workflow_obj
        self._shadow_url = shadow_url
        self._bpmn_component_obj = bpmn_component_obj
        self._workflow_id, _ = split_key(instance_id)
        self._was_sent = False
        self._executor = get_executor()
        # to test failure modes this value will force all
        # calls made to fail.
        self._forcefail = force_fail
        self._forcefail_code = force_fail_code

    def send(self) -> FlowPostResult:
        assert not self._was_sent
        self._was_sent = True
        return self._send()

    def _send(self) -> FlowPostResult:
        headers = self.headers.copy()
        try:
            logging.info(
                f'Making {self.method} to {self.url} for instance {self.instance_id}.'
            )
            response: requests.models.Response = self.req_method(
                self.url,
                data=self.data,
                headers=headers,
                timeout=TIMEOUT,
            )

            if self._forcefail:
                logging.info(f'force failing call with code {self._forcefail_code}')
                response.status_code = self._forcefail_code

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exn:
                logging.exception(
                    f"Instance {self.instance_id} failed on task {self.task_id} {self.url}",
                    exc_info=exn,
                )
                if response.status_code in [502, 503]:
                    return self.raise_connection_error()
                else:
                    return self.raise_task_error(response)
            logging.info(
                f'Successfully made call for {self.instance_id}: {response}.'
            )
            return FlowPostResult(response, FlowPostStatus.SUCCESS)
        except Exception as exn:
            if self.retries > 0:
                self._retries = self.retries - 1
                return self._send()
            else:
                logging.exception(
                    f"Instance {self.instance_id} failed to connect to task on url {self.url}.",
                    exc_info=exn
                )
                return self.raise_connection_error()
        finally:
            self._executor.submit(self.shadow_traffic)

    def shadow_traffic(self):
        """Shadows traffic to the URL specified for this deployment.
        """
        if self.shadow_url == '':
            return

        headers = self._headers.copy()
        parsed_url = urlparse(self.url)
        headers[Headers.X_HEADER_ORIGINAL_HOST] = parsed_url.netloc
        headers[Headers.X_HEADER_ORIGINAL_PATH] = parsed_url.path
        headers[Headers.X_HEADER_TASK_ID] = self.task_id

        logging.info(f"Shadowing traffic to {self.shadow_url} for instance {self.instance_id}.")
        try:
            response = requests.post(self.shadow_url, data=self.data, headers=headers)
            response.raise_for_status()
            logging.info(f"Successfully shadowed traffic on instance {self.instance_id}.")
        except Exception as exn:
            logging.exception(
                f"Failed shadowing traffic on workflow instance {self.instance_id}:",
                exc_info=exn,
            )

    def raise_task_error(self, response: requests.models.Response) -> FlowPostResult:
        """Call this method when the service task failed, and we need to
        transition the WF Instance to the ERROR state.

        The implementation of marking a workflow instance as failed is currently
        handled by making a POST to the /instancefail endpoint of flowd. See
        `flowd/flow_app.py` for the code.
        """
        payload = {
            'from_envoy': False,
            'input_data': FlowPost.jsonify_or_encode_data(self.data),
            'input_headers': dict(self.headers),
            'output_data': FlowPost.jsonify_or_encode_data(response.content),
            'output_headers': dict(response.headers),
            'failed_task_id': self.task_id,
            'error_code': ErrorCodes.FAILED_TASK,
            'error_msg': f'Task {self.task_id} failed.',
        }
        return self._send_error_payload(payload)

    def cancel_instance(self) -> FlowPostResult:
        """Call this method to cancel a workflow instance.

        The implementation of marking a workflow instance as failed is currently
        handled by making a POST to the /instancefail endpoint of flowd. See
        `flowd/flow_app.py` for the code.
        """
        payload = {
            'from_envoy': False,
            'input_data': {},
            'input_headers': {},
            'output_data': {},
            'output_headers': {},
            'failed_instance_id': self.instance_id,
            'error_code': ErrorCodes.CANCELED_INSTANCE,
            'error_msg': f'Instance {self.instance_id} cancelled.',
        }
        return self._send_error_payload(payload)

    def raise_connection_error(self) -> FlowPostResult:
        """This method is called when flowpost tries to make a call to the target service
        but cannot connect. In this case, we must transition the WF Instance to the
        ERROR state with the code ErrorCodes.FAILED_CONNECTION.

        The implementation of marking a workflow instance as failed is currently
        handled by making a POST to the /instancefail endpoint of flowd. See
        `flowd/flow_app.py` for the code.
        """
        payload = {
            'from_envoy': False,
            'input_data': FlowPost.jsonify_or_encode_data(self.data),
            'input_headers': dict(self.headers),
            'failed_task_id': self.task_id,
            'error_code': ErrorCodes.FAILED_CONNECTION,
            'error_msg': f'Could not connect to {self.task_id} on {self.url}.',
        }
        return self._send_error_payload(payload)

    def _send_error_payload(self, payload: dict) -> FlowPostResult:
        """Accepts a dictionary containing a properly-formed message to the flowd
        /instancefail endpoint, and sends it. Returns a FlowPostResult with appropriate
        status depending on whether the success succeeds or fails.
        """
        logging.info(
            f"Sending message to flowd's instancefail endpoint for {self._instance_id}"
        )
        try:
            headers = dict(self.headers.copy())
            headers['content-type'] = 'application/json'
            response = requests.post(
                INSTANCE_FAIL_ENDPOINT,
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return FlowPostResult(None, FlowPostStatus.REPORTED_ERROR)
        except Exception as exn:
            logging.exception(
                f"Failed reporting error for instance {self._instance_id}."
            )
            return FlowPostResult(None, FlowPostStatus.FAILED_TO_REPORT_ERROR)

    @classmethod
    def jsonify_or_encode_data(cls, data: Union[bytes, str]) -> Union[dict, str]:
        """Accepts data and returns it in dict format (via json.loads()) if possible.
        If that is not possible, then this method base64-encodes it and returns it
        in string format.
        """
        try:
            return json.loads(data.decode()) if isinstance(data, bytes) else json.loads(data)
        except Exception as exn:
            logging.exception(
                f"Failed decoding json {data}",
                exc_info=exn,
            )
            to_encode = data if isinstance(data, bytes) else data.encode()
            encoded_bytes = base64.b64encode(to_encode) # type: bytes
            return encoded_bytes.decode()

    @property
    def workflow_obj(self) -> Workflow:
        """Returns the Workflow object that this FlowPost is taking place in.

        Note: computing the Workflow Object can be expensive; therefore, if
        enough data is passed in to the FlowPost constructor, this method
        is not called.
        """
        if self._workflow_obj is None:
            self._workflow_obj = Workflow.from_id(self.workflow_id)
        return self._workflow_obj

    @property
    def bpmn_component_obj(self) -> BPMNComponent:
        """Returns the BPMNComponent Object that we're making a request to.

        Note: computing the BPMNComponent Object can be expensive; therefore, if
        enough data is passed in to the FlowPost constructor, this method
        is not called.
        """
        if self._bpmn_component_obj is None:
            self._bpmn_component_obj = self.workflow_obj.process.component_map[self._task_id]
        return self._bpmn_component_obj

    @property
    def url(self) -> str:
        """Returns the requests.postable() url for the task we're trying to hit
        """
        if self._url is None:
            self._url = self.bpmn_component_obj.k8s_url
        return self._url

    @property
    def method(self) -> str:
        """Returns the lowercase  method with which to call the
        """
        if self._method is None:
            self._method = self.bpmn_component_obj.call_properties.method
        return self._method.lower()

    @property
    def req_method(self) -> Callable:
        """Returns the `requests` method used to call our task.
        """
        if self._req_method is None:
            if self.method == 'post':
                self._req_method = requests.post
            elif self.method == 'patch':
                self._req_method = requests.patch
            elif self.method == 'put':
                self._req_method = requests.put
            elif self.method == 'get':
                self._req_method = requests.get
            else:
                assert self.method == 'delete'
                self._req_method = requests.delete
        return self._req_method

    @property
    def shadow_url(self) -> str:
        """Returns the URL to which we shadow traffic for all requests on this
        Workflow.
        """
        if self._shadow_url is None:
            self._shadow_url = self.workflow_obj.properties.traffic_shadow_url or ''
        return self._shadow_url

    @property
    def retries(self) -> int:
        """Number of retries remaining for this FlowPost.
        """
        if self._retries is None:
            self._retries = self.bpmn_component_obj.call_properties.total_attempts - 1
        return self._retries

    @property
    def data(self) -> Union[str, bytes]:
        """Returns data to send to the task.
        """
        return self._data

    @property
    def headers(self) -> Dict[str, str]:
        """Returns headers to send to the task.
        """
        headers = self._headers.copy()
        headers[Headers.X_HEADER_FLOW_ID] = self.instance_id
        headers[Headers.X_HEADER_TASK_ID] = self.task_id
        headers[Headers.X_HEADER_WORKFLOW_ID] = self.workflow_id
        if 'Host' in headers:
            del headers['Host']
        if 'host' in headers:
            del headers['host']
        return headers

    @property
    def task_id(self) -> str:
        """ID of the BPMNComponent we're flowposting to.
        """
        return self._task_id

    @property
    def instance_id(self) -> str:
        """Instance ID that this request is a part of.
        """
        return self._instance_id

    @property
    def workflow_id(self) -> str:
        """Workflow ID that this request is a part of.
        """
        return self._workflow_id
