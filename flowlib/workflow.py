from ast import literal_eval
from io import StringIO
import json
import logging
import os
import subprocess
from typing import Union
import uuid

from confluent_kafka.admin import AdminClient, NewTopic
import requests
import xmltodict
import yaml

from . import bpmn
from .executor import get_executor
from .etcd_utils import get_etcd, transition_state
from .constants import (
    BStates,
    States,
    WorkflowKeys,
    WorkflowInstanceKeys,
    flow_result,
)


KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")


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
    def from_id(cls, id):
        etcd = get_etcd(is_not_none=True)
        proc_key = WorkflowKeys.proc_key(id)
        proc_bytes = etcd.get(proc_key)[0]
        proc_odict = xmltodict.parse(proc_bytes)['bpmn:process']
        process = bpmn.BPMNProcess(proc_odict)
        return cls(process, id)

    def start(self):
        etcd = get_etcd(is_not_none=True)
        if not etcd.put_if_not_exists(self.keys.state, States.STARTING):
            if not etcd.replace(self.keys.state, States.STOPPED, States.STARTING):
                raise RuntimeError(f'{self.id} is not in a startable state')
        orchestrator = self.properties.orchestrator
        if orchestrator == 'docker':
            docker_compose_input = StringIO()
            self.process.to_docker(docker_compose_input)
            ctl_input = docker_compose_input.getvalue()
            docker_result = subprocess.run(
                ['docker', 'stack', 'deploy', '--compose-file', '-', self.id_hash],
                input=ctl_input, capture_output=True, text=True,
            )
            if docker_result.stdout:
                logging.info(f'Got following output from Docker:\n{docker_result.stdout}')
            if docker_result.returncode != 0:
                logging.error(f'Error from Docker:\n{docker_result.stderr}')
                etcd.replace(self.keys.state, States.STARTING, States.ERROR)
        elif orchestrator in {'kubernetes', 'istio'}:
            kubernetes_input = StringIO()
            if orchestrator == 'kubernetes':
                self.process.to_kubernetes(kubernetes_input, self.id_hash)
            else:
                self.process.to_istio(kubernetes_input, self.id_hash)
                self._create_kafka_topics()
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
        kafka_client = AdminClient({"bootstrap.servers": KAFKA_HOST})
        topic_metadata = kafka_client.list_topics()
        new_topics = [
            NewTopic(topic, num_partitions=3, replication_factor=1)
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
    '''NOTE as of this commit:

    This class does NOT get instantiated by the Start Event, because it requires the
    creation of a Workflow Object. Doing this requires significant computation over the
    BPMN XML, which is slow for large WF's. Rather, the Start Event already knows where
    to send the first request. Furthermore, the Start Event uses the
    `WorkflowInstanceKeys` object to determine which keys to manipulate in Etcd.
    This class is instantiated by Flowd and used for:
    1. Running a WF instance by calling the Start service
    2. Potentially other dashboarding uses in the future (not yet implemented).
    '''
    def __init__(self, parent: Union[str, Workflow], id: str = None):
        if isinstance(parent, str):
            self.parent = Workflow.from_id(parent)
        else:
            self.parent = parent
        self.id = id
        self.keys = WorkflowInstanceKeys(self.id)

    @staticmethod
    def new_instance_id(parent_id: str):
        '''
        Constructs a new WF Instance Id given a parent WF id. Should ONLY be
        called by the Start Service.
        '''
        uid = uuid.uuid1().hex
        return f'{parent_id}-{uid}'

    def start(self, *args):
        '''Starts the WF and returns the resulting ID. NOTE: Now, WF Id's are
        created by the Start Event.
        '''
        process = self.parent.process
        executor_obj = get_executor()

        def start_wf(task_id: str):
            '''
            Arguments:
                task_id - Task ID in the BPMN spec.
            Returns:
                A boolean value indicating an OK response.
            '''
            task = process.component_map[task_id]
            call_props = task.call_properties
            serialization = call_props.serialization.lower()
            eval_args = [literal_eval(arg) for arg in args]
            if serialization == 'json':
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
        target = process.entry_point['@id']
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

        if not etcd.replace(self.keys.state, States.STOPPED, States.STARTING):
            logging.error('Failed to transition from STOPPED -> STARTING.')

        # get headers
        headers = json.loads(etcd.get(self.keys.headers)[0].decode())

        # next, get the json
        payload = json.loads(etcd.get(self.keys.payload)[0].decode())
        headers_to_send = {
            'X-Flow-Id': self.id,
            'X-Rexflow-Wf-Id': self.parent.id,
            'X-Rexflow-Task-Id': headers['X-Rexflow-Task-Id'],
        }

        for k in ['X-B3-Sampled', 'X-Envoy-Internal', 'X-B3-Spanid']:
            if k in headers:
                headers_to_send[k] = headers[k]

        # now, start the thing again.
        response = requests.post(
            f"http://{headers['X-Rexflow-Original-Host']}{headers['X-Rexflow-Original-Path']}",
            json=payload,
            headers=headers_to_send,
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
