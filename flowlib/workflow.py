from ast import literal_eval
from ctypes import c_size_t
from io import StringIO
import json
import logging
import subprocess
from typing import Union
import uuid

import requests
import xmltodict
import yaml

from . import bpmn
from .executor import get_executor
from .etcd_utils import get_etcd, transition_state
from .constants import States


class Workflow:
    def __init__(self, process : bpmn.BPMNProcess, id=None):
        self.process = process
        if id is None:
            uid = uuid.uuid1().hex
            self.id = f'{process.id}-{uid}'
        else:
            self.id = id
        self.id_hash = '%016x' % c_size_t(hash(self.id)).value
        self.key_prefix = f'/rexflow/workflows/{self.id}'
        self.properties = process.properties

    @classmethod
    def from_id(cls, id):
        etcd = get_etcd(is_not_none=True)
        proc_key = f'/rexflow/workflows/{id}/proc'
        proc_bytes = etcd.get(proc_key)[0]
        proc_odict = xmltodict.parse(proc_bytes)['bpmn:process']
        process = bpmn.BPMNProcess(proc_odict)
        return cls(process, id)

    def start(self):
        etcd = get_etcd(is_not_none=True)
        state_key = f'{self.key_prefix}/state'
        if not etcd.put_if_not_exists(state_key, States.STARTING):
            if not etcd.replace(state_key, States.STOPPED, States.STARTING):
                raise RuntimeError(f'{self.id} is not in a startable state')
        print("starting here")
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
                etcd.replace(state_key, States.STARTING, States.ERROR)
        elif orchestrator in {'kubernetes', 'istio'}:
            kubernetes_input = StringIO()
            if orchestrator == 'kubernetes':
                self.process.to_kubernetes(kubernetes_input, self.id_hash)
            else:
                print("calling to istio")
                self.process.to_istio(kubernetes_input, self.id_hash)
                print("done with to istio")
            ctl_input = kubernetes_input.getvalue()
            kubectl_result = subprocess.run(
                ['kubectl', 'apply',
                 '-n', self.process.get_namespace(self.id_hash), '-f', '-'],
                input=ctl_input, capture_output=True, text=True,
            )
            print("done applying")
            if kubectl_result.stdout:
                logging.info(f'Got following output from Kubernetes:\n{kubectl_result.stdout}')
            if kubectl_result.returncode != 0:
                logging.error(f'Error from Kubernetes:\n{kubectl_result.stderr}')
                etcd.replace(state_key, States.STARTING, States.ERROR)
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{orchestrator}"')

    def stop(self):
        etcd = get_etcd(is_not_none=True)
        state_key = f'{self.key_prefix}/state'
        if not transition_state(etcd, state_key, (States.RUNNING, States.ERROR), States.STOPPING):
            raise RuntimeError(f'{self.id} is not in a stoppable state')
        orchestrator = self.properties.orchestrator
        if orchestrator == 'docker':
            docker_result = subprocess.run(
                ['docker', 'stack', 'rm', self.id_hash], capture_output=True, text=True,
            )
            if docker_result.returncode == 0:
                logging.info(f'Got following output from Docker:\n{docker_result.stdout}')
            else:
                logging.error(f'Error from Docker:\n{docker_result.stderr}')
                etcd.replace(state_key, States.STOPPING, States.ERROR)
        elif orchestrator in {'kubernetes', 'istio'}:
            kubernetes_stream = StringIO()
            if orchestrator == 'kubernetes':
                self.process.to_kubernetes(kubernetes_stream, self.id_hash)
            else:
                self.process.to_istio(kubernetes_stream, self.id_hash)
            ctl_input = kubernetes_stream.getvalue()
            kubectl_result = subprocess.run(
                ['kubectl', 'delete',
                 '-n', self.process.get_namespace(self.id_hash), '-f', '-'],
                input=ctl_input, capture_output=True, text=True,
            )
            if kubectl_result.stdout:
                logging.info(f'Got following output from Kubernetes:\n{kubectl_result.stdout}')
            if kubectl_result.returncode != 0:
                logging.error(f'Error from Kubernetes:\n{kubectl_result.stderr}')
                etcd.replace(state_key, States.STOPPING, States.ERROR)
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{orchestrator}"')


class WorkflowInstance:
    def __init__(self, parent : Union[str, Workflow], id:str=None):
        if isinstance(parent, str):
            self.parent = Workflow.from_id(parent)
        else:
            self.parent = parent
        if id is None:
            uid = uuid.uuid1().hex
            self.id = f'flow-{uid}'
        else:
            self.id = id
        self.key_prefix = f'/rexflow/instances/{self.id}'

    def start(self, *args):
        process = self.parent.process
        digraph = process.digraph
        executor_obj = get_executor()
        def start_task(task_id : str):
            '''
            Arguments:
                task_id - Task ID in the BPMN spec.
            Returns:
                A boolean value indicating an OK response.
            '''
            task = process.component_map[task_id]
            call_props = task.call_properties()
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
            if method not in {'post',}:
                raise ValueError(f'{method} is not a supported method.')
            request = getattr(requests, method)
            response = request(
                task.k8s_url(),
                headers={'X-Flow-ID':self.id, 'Content-Type':mime_type},
                data=data
            )
            if response.ok:
                logging.info(f"Response for {task_id} in {self.id} was OK.")
            else:
                logging.error(f"Response for {task_id} in {self.id} was not OK.  (status code {response.status_code})")
            return response.ok
        targets = [target_id
            for target_id in digraph[process.entry_point['@id']]
            if target_id.startswith('Task') # TODO: Handle other vertex types...
        ]
        results = executor_obj.map(start_task, targets)
        all_ok = all(result for result in results)
        etcd = get_etcd(is_not_none=True)
        if not all_ok:
            if not etcd.replace(f'{self.key_prefix}/state', States.STARTING, States.ERROR):
                logging.error('Failed to transition from STARTING -> ERROR.')
        else:
            if not etcd.replace(f'{self.key_prefix}/state', States.STARTING, States.RUNNING):
                logging.error('Failed to transition from STARTING -> RUNNING.')

    def stop(self):
        raise NotImplementedError('Lazy developer error!')
