from concurrent.futures import wait
import logging
import time

from etcd3.events import DeleteEvent, PutEvent
from flask import Flask, jsonify, request
import requests

from flowlib.etcd_utils import get_etcd, get_next_level
from flowlib.executor import get_executor
from flowlib.flowd_utils import get_log_format
from flowlib.workflow import Workflow


app = Flask(__name__)

executor = get_executor()

etcd = get_etcd()


class HealthProbe:
    def __init__(self, workflow, task):
        self.workflow = workflow
        self.task = task
        self.key = f'/rexflow/workflows/{workflow.id}/probes/{task.id}'
        self.future = None
        self.running = False
        self.status = None
        self.logger = logging.getLogger()
        health_properties = task.definition.health
        service_properties = task.definition.service
        protocol = service_properties.protocol.lower()
        host = service_properties.host
        port = service_properties.port
        path = (health_properties.path
                if health_properties.path.startswith('/')
                else f'/{health_properties.path}')
        self.url = f'{protocol}://{host}:{port}{path}'

    def __call__(self):
        self.logger.info(f'Starting status checks for {self.task.id}')
        health_properties = self.task.definition.health
        while self.running:
            time.sleep(health_properties.period)
            if not self.running:
                break
            # FIXME: The above should fix a majority of races with a stopping
            # workflow.  It, however, does not fix all races and healthd may
            # still pollute etcd with a final put before stopping fully.
            try:
                response = requests.request(
                    health_properties.method, self.url,
                    data=health_properties.query
                )
                exception = None
            except requests.RequestException as exn:
                exception = exn
                response = exn.response
            result = 'UP' if exception is None and response.ok else 'DOWN'
            etcd.put(self.key, result)
            self.status = result
            self.logger.info(f'Status check for {self.task.id} is {result}')
        return result

    def start(self):
        assert self.future is None
        self.running = True
        self.future = executor.submit(self)

    def stop(self):
        assert self.future is not None
        self.running = False


class HealthManager:
    def __init__(self):
        self.workflows = {workflow_id : Workflow.from_id(workflow_id)
            for workflow_id in get_next_level('/rexflow/workflows')
        }
        self.probes = {}
        self.future = None
        self.logger = logging.getLogger()

    def __call__(self):
        watch_iter, cancel_watch = etcd.watch_prefix('/rexflow/workflows')
        for event in watch_iter:
            key = event.key.decode('utf-8')
            if key.endswith('/state'):
                workflow_id = key.split('/')[3]
                if isinstance(event, PutEvent):
                    value = event.value.decode('utf-8')
                    if value == 'STARTING':
                        assert workflow_id not in self.workflows.keys()
                        workflow = Workflow.from_id(workflow_id)
                        self.workflows[workflow_id] = workflow
                        self.probes[workflow_id] = {
                            task.id : HealthProbe(workflow, task)
                            for task in workflow.process.tasks
                        }
                        for probe in self.probes[workflow_id].values():
                           probe.start()
                        future = executor.submit(self.wait_for_up, workflow)
                    elif value == 'STOPPING':
                        workflow = self.workflows[workflow_id]
                        future = executor.submit(self.wait_for_down, workflow)
                elif isinstance(event, DeleteEvent):
                    pass

    def wait_for_up(self, workflow : Workflow):
        self.logger.info(f'wait_for_up() called for workflow {workflow.id}')
        probes = self.probes[workflow.id]
        watch_iter, _ = etcd.watch_prefix(f'{workflow.key_prefix}/probes')
        for event in watch_iter:
            self.logger.info(f'wait_for_up(): Got {type(event)} to key {event.key}')
            if isinstance(event, PutEvent):
                if all(probe.status == 'UP' for probe in probes.values()):
                    result = etcd.replace(f'{workflow.key_prefix}/state', 'STARTING', 'RUNNING')
                    if result:
                        self.logger.info('wait_for_up(): State transition succeeded.')
                    else:
                        self.logger.error('wait_for_up(): State transition failed.')
                    return result
        return False

    def wait_for_down(self, workflow : Workflow):
        self.logger.info(f'wait_for_down() called for workflow {workflow.id}')
        probes = self.probes[workflow.id]
        watch_iter, _ = etcd.watch_prefix(f'/rexflow/workflows/{workflow.id}/probes/')
        for event in watch_iter:
            self.logger.info(f'wait_for_down(): Got {type(event)} to key {event.key}')
            if isinstance(event, PutEvent):
                if all(probe.status == 'DOWN' for probe in probes.values()):
                    for probe in probes.values():
                        probe.stop()
                    del self.probes[workflow.id]
                    del self.workflows[workflow.id]
                    result = etcd.replace(f'{workflow.key_prefix}/state', 'STOPPING', 'STOPPED')
                    if result:
                        self.logger.info('wait_for_down(): State transition succeeded.')
                    else:
                        self.logger.error('wait_for_down(): State transition failed.')
                    return result
        return False

    def start(self):
        for workflow in self.workflows.values():
            probes = {
                task.id : HealthProbe(workflow, task)
                for task in workflow.process.tasks
            }
            for probe in probes.values():
                probe.start()
            self.probes[workflow.id] = probes
            workflow_state = etcd.get(workflow.key_prefix + '/state')[0].decode()
            self.logger.info(f'Started probes for {workflow.id}, in state {workflow_state}')
            if workflow_state == 'STARTING':
                executor.submit(self.wait_for_up, workflow)
            elif workflow_state == 'STOPPING':
                executor.submit(self.wait_for_down, workflow)
        self.future = executor.submit(self)

    def stop(self):
        probes = [
            probe
            for probe in probes.values()
            for probes in self.probes[workflow.id]
            for workflow in self.workflows
        ]
        for probe in probes:
            probe.stop()
        # FIXME: Bring the manager future down cleanly.


manager = HealthManager()


@app.route('/')
def root_route():
    return jsonify({workflow_id : {
        task_id : str(probe) for task_id, probe in manager.probes[workflow_id].items()
    } for workflow_id in manager.workflows.keys()})


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    logging.basicConfig(format=get_log_format('healthd'), level=logging.INFO)
    manager.start()
    app.run(host='0.0.0.0', port=5050)
