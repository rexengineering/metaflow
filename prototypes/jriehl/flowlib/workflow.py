from ast import literal_eval
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from ctypes import c_size_t
from io import StringIO
import json
import logging
import multiprocessing
import subprocess
import time
import uuid

import requests
import xmltodict
import yaml

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
        if not etcd.put_if_not_exists(state_key, 'STARTING'):
            if not etcd.replace(state_key, 'STOPPED', 'STARTING'):
                raise RuntimeError(f'{self.id} is not in a startable state')
        if self.properties.orchestrator == 'docker':
            docker_compose_input = StringIO()
            self.process.to_docker(docker_compose_input)
            docker_result = subprocess.run(
                ['docker', 'stack', 'deploy', '--compose-file', '-', self.id_hash],
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
                ['docker', 'stack', 'rm', self.id_hash], capture_output=True, text=True,
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
    def __init__(self, parent : (str, Workflow), id:str=None):
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
        def start_task(task_id):
            '''
            Arguments:
                task_id - Task ID in the BPMN spec.
            Returns:
                A boolean value indicating an OK response.
            '''
            task = process.tasks.task_map[task_id]
            call_props = task.definition.call
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
                task.url,
                headers={'X-Flow-ID':self.id, 'Content-Type':mime_type},
                data=data
            )
            if not response.ok:
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
            if not etcd.replace(f'{self.key_prefix}/state', 'STARTING', 'ERROR'):
                logging.error('Failed to transition from STARTING -> ERROR.')
        else:
            if not etcd.replace(f'{self.key_prefix}/state', 'STARTING', 'RUNNING'):
                logging.error('Failed to transition from STARTING -> RUNNING.')

    def stop(self):
        raise NotImplementedError('Lazy developer error!')
