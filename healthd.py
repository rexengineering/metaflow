import logging
import time

from etcd3.events import DeleteEvent, PutEvent
from quart import jsonify
import requests

from flowlib.bpmn_util import BPMNComponent
from flowlib.etcd_utils import get_etcd, get_next_level
from flowlib.executor import get_executor
from flowlib.flowd_utils import get_log_format
from flowlib.quart_app import QuartApp
from flowlib.workflow import Workflow
from flowlib.constants import States, BStates, WorkflowKeys


class HealthProbe:
    def __init__(self, workflow: Workflow, task: BPMNComponent):
        self.workflow = workflow
        self.task = task
        self.key = WorkflowKeys.task_key(workflow.id, task.id)
        self.future = None
        self.running = False
        self.status = None
        self.logger = logging.getLogger()
        self.etcd = get_etcd()
        self.executor = get_executor()
        self.url = self.task.k8s_url

    def __call__(self):
        self.logger.info(f'Starting status checks for {self.task.id} ({self.url})')
        health_properties = self.task.health_properties
        result = ''
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
            self.etcd.put(self.key, result)
            self.status = result
            self.logger.info(f'Status check for {self.task.id} is {result}')
        return result

    def start(self):
        assert self.future is None
        self.running = True
        self.future = self.executor.submit(self)

    def stop(self):
        assert self.future is not None
        self.running = False


class HealthManager:
    def __init__(self):
        self.etcd = get_etcd()
        self.executor = get_executor()
        self.workflows = {
            workflow_id: Workflow.from_id(workflow_id)
            for workflow_id in get_next_level(WorkflowKeys.ROOT)
        }
        self.probes = {}
        self.future = None
        self.cancel_watch = None
        self.logger = logging.getLogger()

    def __call__(self):
        watch_iter, self.cancel_watch = self.etcd.watch_prefix(WorkflowKeys.ROOT)
        for event in watch_iter:
            key = event.key.decode('utf-8')
            if key.endswith('/state'):
                workflow_id = key.split('/')[3]
                if isinstance(event, PutEvent):
                    value = event.value.decode('utf-8')
                    if value == States.STARTING:
                        assert workflow_id not in self.workflows.keys()
                        workflow = Workflow.from_id(workflow_id)
                        self.workflows[workflow_id] = workflow
                        self.probes[workflow_id] = {
                            component.id: HealthProbe(workflow, component)
                            for component in workflow.process.all_components
                        }
                        for probe in self.probes[workflow_id].values():
                            probe.start()
                        self.future = self.executor.submit(self.wait_for_up, workflow)
                    elif value == States.STOPPING:
                        workflow = self.workflows[workflow_id]
                        self.future = self.executor.submit(self.wait_for_down, workflow)
                elif isinstance(event, DeleteEvent):
                    self.logger.info(f'{workflow_id} DELETE event - {value}')
                    for probe in self.probes[workflow_id].values():
                        probe.stop()

    def wait_for_up(self, workflow: Workflow):
        self.logger.info(f'wait_for_up() called for workflow {workflow.id}')
        probes = self.probes[workflow.id]
        watch_iter, _ = self.etcd.watch_prefix(workflow.keys.probe)
        for event in watch_iter:
            self.logger.info(f'wait_for_up(): Got {type(event)} to key {event.key}')
            crnt_state = self.etcd.get(workflow.keys.state)[0]
            if (crnt_state is None) or (crnt_state != BStates.STARTING):
                self.logger.info(f'wait_for_up(): Workflow {workflow.id} is no '
                                 'longer starting up, cancelling further '
                                 'monitoring.')
                break
            if isinstance(event, PutEvent):
                if all(probe.status == 'UP' for probe in probes.values()):
                    result = self.etcd.replace(workflow.keys.state,
                                               States.STARTING, States.RUNNING)
                    if result:
                        self.logger.info('wait_for_up(): State transition succeeded.')
                    else:
                        self.logger.error('wait_for_up(): State transition failed.')
                    return result
        return False

    def wait_for_down(self, workflow: Workflow):
        self.logger.info(f'wait_for_down() called for workflow {workflow.id}')
        probes = self.probes[workflow.id]
        watch_iter, _ = self.etcd.watch_prefix(workflow.keys.probe)
        for event in watch_iter:
            self.logger.info(f'wait_for_down(): Got {type(event)} to key {event.key}')
            if isinstance(event, PutEvent):
                if all(probe.status == 'DOWN' for probe in probes.values()):
                    for probe in probes.values():
                        probe.stop()
                    del self.probes[workflow.id]
                    del self.workflows[workflow.id]
                    result = self.etcd.replace(workflow.keys.state,
                                               States.STOPPING, States.STOPPED)
                    if result:
                        self.logger.info('wait_for_down(): State transition succeeded.')
                    else:
                        self.logger.error('wait_for_down(): State transition failed.')
                    return result
        return False

    def start(self):
        for workflow in self.workflows.values():
            probes = {
                task.id: HealthProbe(workflow, task)
                for task in workflow.process.tasks
            }
            for probe in probes.values():
                probe.start()
            self.probes[workflow.id] = probes
            workflow_state = self.etcd.get(workflow.keys.state)[0].decode()
            self.logger.info(f'Started probes for {workflow.id}, in state {workflow_state}')
            if workflow_state == States.STARTING:
                self.executor.submit(self.wait_for_up, workflow)
            elif workflow_state == States.STOPPING:
                self.executor.submit(self.wait_for_down, workflow)
        self.future = self.executor.submit(self)

    def stop(self):
        probes = [
            probe
            for workflow in self.workflows.values()
            for probe in self.probes[workflow.id].values()
        ]
        for probe in probes:
            probe.stop()
        if self.cancel_watch:
            self.cancel_watch()


class HealthApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = HealthManager()
        self.app.route('/')(self.root_route)

    def root_route(self):
        return jsonify({workflow_id: {
            task_id: str(probe)
            for task_id, probe in self.manager.probes[workflow_id].items()
        } for workflow_id in self.manager.workflows.keys()})

    def _shutdown(self):
        self.manager.stop()

    def run(self):
        self.manager.start()
        super().run()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    logging.basicConfig(format=get_log_format('healthd'), level=logging.INFO)
    app = HealthApp(bind='0.0.0.0:5050')
    app.run()
