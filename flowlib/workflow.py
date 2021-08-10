from ast import literal_eval
import functools
from io import StringIO
import json
import logging
import subprocess
from typing import List, Union
import uuid

from confluent_kafka.admin import AdminClient, NewTopic
import requests
import xmltodict
import yaml

from . import bpmn
from .bpmn_util import BPMN
from .executor import get_executor
from .etcd_utils import get_etcd, transition_state
from .constants import (
    BStates,
    States,
    WorkflowKeys,
    WorkflowInstanceKeys,
    flow_result,
)

from .config import get_kafka_config


KAFKA_CONFIG = get_kafka_config()


def get_workflows() -> List['Workflow']:
    etcd = get_etcd(is_not_none=True)
    wf_keys = [
        wf_kv[1].key.decode()
        for wf_kv in etcd.get_prefix(WorkflowKeys.ROOT, keys_only=True)
    ]
    wf_dids = set(wf_key.split('/')[3] for wf_key in wf_keys)
    return [Workflow.from_id(wf_did) for wf_did in wf_dids]


class Workflow:
    def __init__(self, process: bpmn.BPMNProcess, id=None):
        self.process = process
        if id is None:
            self.id = self.process.id
        else:
            self.id = id
        self.keys = WorkflowKeys(self.id)
        self.properties = process.properties
        self.id_hash = self.properties.id_hash

    @classmethod
    @functools.lru_cache(maxsize=80)
    def from_id(cls, id):
        etcd = get_etcd(is_not_none=True)

        proc_key = WorkflowKeys.proc_key(id)
        proc_bytes = etcd.get(proc_key)[0]
        proc_odict = xmltodict.parse(proc_bytes)[BPMN.process]
        process = bpmn.BPMNProcess(proc_odict)
        return cls(process, id)

    def start(self):
        etcd = get_etcd(is_not_none=True)
        if not etcd.put_if_not_exists(self.keys.state, States.STARTING):
            if not etcd.replace(self.keys.state, States.STOPPED, States.STARTING):
                raise RuntimeError(f'{self.id} is not in a startable state')
        orchestrator = self.properties.orchestrator
        if orchestrator in {'kubernetes', 'istio'}:
            kubernetes_input = StringIO()
            try:
                if orchestrator == 'kubernetes':
                    self.process.to_kubernetes(kubernetes_input, self.id_hash)
                else:
                    self.process.to_istio(kubernetes_input, self.id_hash)
                    self._create_kafka_topics()
            except Exception as exn:
                etcd.put(self.keys.state, States.ERROR)
                raise exn
            ctl_input = kubernetes_input.getvalue()
            kubectl_result = subprocess.run(
                ['kubectl', 'apply', '-f', '-'],
                input=ctl_input, capture_output=True, text=True,
            )
            if kubectl_result.stdout:
                logging.info(f'Got following output from Kubernetes:\n{kubectl_result.stdout}')
            if kubectl_result.returncode != 0:
                logging.error(f'Error from Kubernetes:\n{kubectl_result.stderr}')
                etcd.replace(self.keys.state, States.STARTING, States.ERROR)
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{orchestrator}"')

    def _create_kafka_topics(self):
        if KAFKA_CONFIG is None or len(self.process.kafka_topics) == 0:
            return
        kafka_client = AdminClient(KAFKA_CONFIG)
        topic_metadata = kafka_client.list_topics()
        new_topics = [
            # Let the rexflow user's own kafka deployment decide upon
            # sensible defaults for replication factors.
            NewTopic(topic, num_partitions=3)
            for topic in self.process.kafka_topics
            if topic_metadata.topics.get(topic) is None
        ]
        if len(new_topics):
            response = kafka_client.create_topics(new_topics)
            for topic, f in response.items():
                try:
                    f.result()  # The result itself is None
                    logging.info(f"Created Kafka Topic {topic}.")
                except Exception as e:
                    logging.error(f"Failed to create topic {topic}: {e}")

    def _delete_kafka_topics(self):
        if KAFKA_CONFIG is None or len(self.process.kafka_topics) == 0:
            return
        kafka_client = AdminClient(KAFKA_CONFIG)
        topic_metadata = kafka_client.list_topics()
        topics_to_delete = [
            topic for topic in self.process.kafka_topics
            if topic_metadata.topics.get(topic) is not None
        ]
        if len(topics_to_delete):
            response = kafka_client.delete_topics(topics_to_delete)
            for topic, f in response.items():
                try:
                    f.result()  # The result itself is None
                    logging.info(f"Deleted Kafka Topic {topic}.")
                except Exception as e:
                    logging.error(f"Failed to delete topic {topic}: {e}")
        else:
            logging.info("no kafka topics to delete.")

    def stop(self):
        etcd = get_etcd(is_not_none=True)
        good_states = (BStates.RUNNING, BStates.ERROR)
        if not transition_state(etcd, self.keys.state, good_states, BStates.STOPPING):
            raise RuntimeError(f'{self.id} is not in a stoppable state')

    def remove(self):
        logging.info(f'Removing deployment for workflow {self.id}')
        etcd = get_etcd(is_not_none=True)
        orchestrator = self.properties.orchestrator
        logging.info(f'orchestrator is {orchestrator}')
        if orchestrator == 'docker':
            docker_result = subprocess.run(
                ['docker', 'stack', 'rm', self.id_hash], capture_output=True, text=True,
            )
            if docker_result.returncode == 0:
                logging.info(f'Got following output from Docker:\n{docker_result.stdout}')
            else:
                logging.error(f'Error from Docker:\n{docker_result.stderr}')
                etcd.replace(self.keys.state, States.STOPPING, States.ERROR)
        elif orchestrator in {'kubernetes', 'istio'}:
            # TODO: Rethink when to delete kafka topics since more than
            # one deployment may use a given topic.
            kubernetes_stream = StringIO()
            if orchestrator == 'kubernetes':
                self.process.to_kubernetes(kubernetes_stream, self.id_hash)
            else:
                self.process.to_istio(kubernetes_stream, self.id_hash)
            ctl_input = kubernetes_stream.getvalue()
            kubectl_result = subprocess.run(
                ['kubectl', 'delete', '--ignore-not-found', '-f', '-'],
                input=ctl_input, capture_output=True, text=True,
            )
            if kubectl_result.stdout:
                logging.info(f'Got following output from Kubernetes:\n{kubectl_result.stdout}')
            if kubectl_result.returncode != 0:
                logging.error(f'Error from Kubernetes:\n{kubectl_result.stderr}')
                etcd.replace(self.keys.state, States.STOPPING, States.ERROR)
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{orchestrator}"')


class WorkflowInstance:
    """NOTE as of this commit:

    This class does NOT get instantiated by the Start Event, because it requires the
    creation of a Workflow Object. Doing this requires significant computation over the
    BPMN XML, which is slow for large WF's. Rather, the Start Event already knows where
    to send the first request. Furthermore, the Start Event uses the
    `WorkflowInstanceKeys` object to determine which keys to manipulate in Etcd.
    This class is instantiated by Flowd and used for:
    1. Running a WF instance via `flowctl run` as opposed to an http call to Start Event.
    2. Potentially other dashboarding uses in the future (not yet implemented).
    """
    def __init__(self, parent: Union[str, Workflow], id: str = None):
        if isinstance(parent, str):
            self.parent = Workflow.from_id(parent)
        else:
            self.parent = parent
        self.id = id
        self.keys = WorkflowInstanceKeys(self.id)

    @staticmethod
    def new_instance_id(parent_id: str):
        """
        Constructs a new WF Instance Id given a parent WF id. Should ONLY be
        called by the Start Service.
        """
        uid = uuid.uuid1().hex
        return f'{parent_id}-{uid}'

    def start(self, start_event_id=None, *args):
        """Starts the WF and returns the resulting ID. NOTE: Now, WF Id's are
        created by the Start Event, so this method simply makes an HTTP rpc call
        to the appropriate start event of the appropriate WF Deployment.
        """
        process = self.parent.process
        executor_obj = get_executor()

        def start_wf(task_id: str):
            """
            Arguments:
                task_id - Task ID in the BPMN spec.
            Returns:
                A boolean value indicating an OK response.
            """
            task = process.component_map[task_id]
            call_props = task.call_properties
            serialization = call_props.serialization.lower()
            eval_args = [literal_eval(arg) for arg in args]
            if serialization == 'json':
                if eval_args == []:
                    eval_args = {}
                data = json.dumps(eval_args)
                mime_type = 'application/json'
            elif serialization == 'yaml':
                data = yaml.dump(eval_args)
                mime_type = 'application/x-yaml'
            else:
                raise ValueError(f'{serialization} is not a supported serialization type.')
            method = call_props.method.lower()
            if method not in {'post'}:
                raise ValueError(f'{method} is not a supported method.')
            request = getattr(requests, method)
            req_headers = {
                'X-Flow-ID': self.id,
                'X-Rexflow-Wf-Id': self.parent.id,
                'Content-Type': mime_type
            }
            response = request(
                task.k8s_url,
                headers=req_headers,
                data=data
            )
            if response.ok:
                logging.info(f"Response for {task_id} in {self.id} was OK.")
            else:
                logging.error(
                    f"Response for {task_id} in {self.id} was not OK."
                    f"(status code {response.status_code})"
                )
            return response

        target = None
        if len(process.entry_points) > 1:
            start_event_ids = [ep['@id'] for ep in process.entry_points]
            if start_event_id not in start_event_ids:
                message = "Must choose between following start events: "
                message += ', '.join(start_event_ids)
                message += '. Use --start_event_id'
                return {
                    "status": -1,
                    "message": message
                }
            target = start_event_id
        else:
            target = process.entry_points[0]['@id']

        future = executor_obj.submit(start_wf, target)

        etcd = get_etcd(is_not_none=True)
        response = future.result()

        if not response.ok:
            if not etcd.replace(self.keys.state, States.STARTING, States.ERROR):
                logging.error('Failed to transition from STARTING -> ERROR.')
            return {"instance_id": "Error"}
        else:
            if not etcd.replace(self.keys.state, States.STARTING, States.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')
            return response.json()

    def retry(self):
        # mark running
        etcd = get_etcd()

        try:
            payload = json.loads(etcd.get(self.keys.result)[0].decode())
            headers = payload['input_headers']
            data = payload['input_data']
            failed_task_id = payload['failed_task_id']
            component = self.parent.process.component_map[failed_task_id]
            etcd.delete(self.keys.result)
        except Exception as exn:
            logging.exception(
                f'Failed loading previous state when retrying WF Instance {self.id}.',
                exc_info=exn,
            )
            return flow_result(-1, "Failed to load previous instance state from before failure.")

        if not etcd.replace(self.keys.state, States.STOPPED, States.STARTING):
            logging.error('Failed to transition from STOPPED -> STARTING.')

        # now, start the thing again.
        response = requests.post(
            component.k8s_url,
            json=data,  # TODO: Handle more than just JSON mimetype.
            headers=headers,
        )

        msg = "Retry Succeeded."
        if response.ok:
            if not etcd.replace(self.keys.state, States.STARTING, States.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')
            status = 0
        else:
            if not etcd.replace(self.keys.state, States.STARTING, States.STOPPED):
                logging.error('Failed to transition from RUNNING -> ERROR.')
            msg = "Retry failed."
            status = -1

        return flow_result(status, msg)

    def stop(self):
        raise NotImplementedError('Lazy developer error!')
