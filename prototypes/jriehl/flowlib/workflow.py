from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import logging
import multiprocessing
import subprocess
import time
import uuid

import requests
import xmltodict

from . import bpmn
from .executor import get_executor
from .etcd_utils import get_etcd, transition_state


class Workflow:
    def __init__(self, process : bpmn.BPMNProcess, id=None):
        self.process = process
        if id is None:
            uid = uuid.uuid1().hex
            self.id = f'{process.id}-{uid}'
        else:
            self.id = id
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
        if not etcd.put_if_not_exists(state_key, 'STARTING'):
            if not etcd.replace(state_key, 'STOPPED', 'STARTING'):
                raise RuntimeError(f'{self.id} is not in a startable state')
        if self.properties.orchestrator == 'docker':
            docker_compose_input = StringIO()
            self.process.tasks.to_docker(docker_compose_input)
            docker_result = subprocess.run(
                ['docker', 'stack', 'deploy', '--compose-file', '-', self.id],
                input=docker_compose_input.getvalue(), capture_output=True,
                text=True,
            )
            if docker_result.returncode == 0:
                logging.info(f'Got following output from Docker:\n{docker_result.stdout}')
            else:
                logging.error(f'Error from Docker:\n{docker_result.stderr}')
                etcd.replace(state_key, 'STARTING', 'ERROR')
        elif self.properties.orchestrator == 'kubernetes':
            raise NotImplementedError('Lazy developer error!')
        elif self.properties.orchestrator == 'istio':
            raise NotImplementedError('Lazy developer error!')
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{self.properties.orchestrator}"')

    def stop(self):
        etcd = get_etcd()
        state_key = f'{self.key_prefix}/state'
        if not transition_state(etcd, state_key, (b'RUNNING', b'ERROR'), b'STOPPING'):
            raise RuntimeError(f'{self.id} is not in a stoppable state')
        if self.properties.orchestrator == 'docker':
            docker_result = subprocess.run(
                ['docker', 'stack', 'rm', self.id], capture_output=True, text=True,
            )
            if docker_result.returncode == 0:
                logging.info(f'Got following output from Docker:\n{docker_result.stdout}')
            else:
                logging.error(f'Error from Dockers:\n{docker_result.stderr}')
                etcd.replace(state_key, 'STOPPING', 'ERROR')
        elif self.properties.orchestrator == 'kubernetes':
            raise NotImplementedError('Lazy developer error!')
        elif self.properties.orchestrator == 'istio':
            raise NotImplementedError('Lazy developer error!')
        else:
            raise ValueError(f'Unrecognized orchestrator setting, "{self.properties.orchestrator}"')


class WorkflowInstance:
    def __init__(self, parent : str, id:str=None):
        self.parent = parent
        if id is None:
            uid = uuid.uuid1().hex
            self.id = f'flow-{uid}'
        else:
            self.id = id
        self.key_prefix = f'/rexflow/isntances/{self.id}'
