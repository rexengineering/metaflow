import logging
import threading
import time

from etcd3.events import DeleteEvent, PutEvent
from quart import jsonify
import requests

from flowlib.bpmn_util import BPMNComponent
from flowlib.etcd_utils import get_etcd, get_next_level, get_keys_from_prefix
from flowlib.executor import get_executor
from flowlib.flowd_utils import get_log_format
from flowlib.quart_app import QuartApp
from flowlib.workflow import Workflow
from flowlib.constants import States, BStates, WorkflowKeys, WorkflowInstanceKeys


class HealthProbe:
    def __init__(self, workflow: Workflow, task: BPMNComponent):
        self.workflow = workflow
        self.task = task
        self.key = WorkflowKeys.task_key(workflow.id, task.id)
        self.timer = None
        self.running = False
        self.status = None
        self.logger = logging.getLogger()
        self.etcd = get_etcd()
        self.wf_state_key = WorkflowKeys.state_key(workflow.id)
        health_path = self.task.health_properties.path
        if not health_path.startswith('/'):
            health_path = '/' + health_path
        self.url = f'http://{self.task.envoy_host}:{self.task.service_properties.port}{health_path}'

    def __call__(self):
        health_properties = self.task.health_properties
        try:
            response = requests.request(
                health_properties.method, self.url,
                data=health_properties.query, timeout=health_properties.timeout,
            )
            exception = None
        except requests.RequestException as exn:
            exception = exn
            response = exn.response
        result = 'UP' if exception is None and response.ok else 'DOWN'

        success, _ = self.etcd.transaction(
            compare=[
                # arcane syntax from the etcd3 library...doesn't do what you think
                # https://github.com/kragniz/python-etcd3/blob/master/etcd3/transactions.py
                self.etcd.transactions.value(self.wf_state_key) != b''
            ],
            success=[self.etcd.transactions.put(self.key, result)],
            failure=[],
        )
        if not success:
            logging.warning(
                f"Probe for task {self.task.id} {self.workflow.id} was orphaned."
            )
            self.stop()
            return

        self.status = result
        self.logger.info(f'Status check for {self.task.id} is {result}')
        if self.running:
            self.timer = threading.Timer(self.task.health_properties.period, self)
            self.timer.start()
        return [self.task.id, self.status]

    def start(self):
        self.logger.info(f'Starting status checks for {self.task.id} ({self.url})')
        assert self.timer is None
        self.timer = threading.Timer(self.task.health_properties.period, self)
        self.running = True
        self.timer.start()

    def stop(self):
        if self.timer is not None:
            logging.info(
                f"shutting down probe for BPMNComponent {self.task.id}"
            )
            self.timer.cancel()
        else:
            logging.warning(
                f"at shutdown, no threading.timer for probe {self.task.id}"
            )
        self.etcd.delete(self.key)


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
            value = event.value.decode('utf-8')
            if key.endswith('/state'):
                workflow_id = key.split('/')[3]
                if isinstance(event, PutEvent):
                    if value == States.STARTING:
                        assert workflow_id not in self.workflows.keys()
                        workflow = Workflow.from_id(workflow_id)
                        self.workflows[workflow_id] = workflow
                        self.probes[workflow_id] = {
                            component.id: HealthProbe(workflow, component)
                            for component in workflow.process.all_components
                            if component.health_properties is not None
                        }
                        for probe in self.probes[workflow_id].values():
                            probe.start()
                        self.future = self.executor.submit(self.wait_for_up, workflow)
                    elif value == States.STOPPING:
                        workflow = self.workflows[workflow_id]
                        self.future = self.executor.submit(self.stop_workflow, workflow)
                elif isinstance(event, DeleteEvent):
                    self.logger.info(f'{workflow_id} DELETE event - {value}')
                    # No action necessary because we stop the HealthProbes in the
                    # stop_workflow() function. This is good practice because we don't want
                    # a bunch of HealthProbes making calls to services that don't exist.

    def wait_for_up(self, workflow: Workflow):
        '''Waits for workflow to come up. If the workflow does not come up within the timeout
        (defined in the `WorkflowProperties`) then the workflow is transitioned to ERROR state.
        However, the Workflow can still be transitioned from ERROR to RUNNING if a probe
        succeeds afterwards.
        '''
        def timeout_catch():
            if not self.etcd.replace(workflow.keys.state, States.STARTING, States.ERROR):
                logging.info(
                    f"Appears that {workflow.id} came up before timeout."
                )
            else:
                logging.error(
                    f"Workflow {workflow.id} did not come up in time; transitioned to ERROR state."
                )
        try:
            self.logger.info(f'wait_for_up() called for workflow {workflow.id}')
            probes = self.probes[workflow.id]
            watch_iter, _ = self.etcd.watch_prefix(workflow.keys.probe)

            timeout_timer = threading.Timer(
                workflow.properties.deployment_timeout, timeout_catch)
            timeout_timer.start()

            for event in watch_iter:
                self.logger.info(f'wait_for_up(): Got {type(event)} to key {event.key}')
                crnt_state = self.etcd.get(workflow.keys.state)[0]
                if (crnt_state is None) or (crnt_state not in {BStates.STARTING, BStates.ERROR}):
                    self.logger.info(f'wait_for_up(): Workflow {workflow.id} is no '
                                    'longer starting up, cancelling further '
                                    'monitoring.')
                    break
                if isinstance(event, PutEvent):
                    if all(probe.status == 'UP' for probe in probes.values()):
                        result = self.etcd.replace(workflow.keys.state,
                                                   crnt_state, States.RUNNING)
                        if result:
                            self.logger.info('wait_for_up(): State transition succeeded.')
                        else:
                            self.logger.error('wait_for_up(): State transition failed.')
                        return result
        except Exception as exn:
            logging.exception(f"failed on the waiting for up on {workflow.id}", exc_info=exn)
            if not self.etcd.replace(workflow.keys.state, States.STARTING, States.ERROR):
                logging.error(
                    f"Couldn't transition wf {workflow.id} to ERROR state."
                )
            return False

    def wait_for_down(self, workflow: Workflow):
        self.logger.info(f'wait_for_down() called for workflow {workflow.id}')
        probes = self.probes[workflow.id]
        watch_iter, cancel = self.etcd.watch_prefix(workflow.keys.probe)

        timeout_timer = threading.Timer(
            workflow.properties.deployment_timeout, cancel)
        timeout_timer.start()

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

        # If we got here, then the deployment timed out before coming down.
        if not self.etcd.replace(workflow.keys.state, States.STOPPING, States.ERROR):
            logging.error(
                f"Couldn't transition wf {workflow.id} to ERROR state."
            )

        return False

    def stop_workflow(self, workflow: Workflow):
        '''
        Stopping a workflow means we need to wait for all the instances for that
        workflow to COMPLETE or ERROR. Then we need to delete the deployment for
        the workflow, and finally wait for all those tasks to go DOWN before
        finally marking the workflow as STOPPED.

        TODO: Do we need to enforce a timeout?
        '''
        self.logger.info(f'stop_workflow {workflow.id}')

        try:
            self.logger.info(f'Removing workflow {workflow.id}')
            workflow.remove()
        except Exception as exn:
            logging.exception(
                f"Failed to bring down workflow {workflow.id}",
                exc_info=exn,
            )
            self.etcd.replace(workflow.keys.state, BStates.STOPPING, BStates.ERROR)
        return self.wait_for_down(workflow)

    def start(self):
        for workflow in self.workflows.values():
            probes = {
                component.id: HealthProbe(workflow, component)
                for component in workflow.process.all_components
                if component.health_properties is not None
            }
            for probe in probes.values():
                probe.start()
            self.probes[workflow.id] = probes
            workflow_state = self.etcd.get(workflow.keys.state)[0].decode()
            self.logger.info(f'Started probes for {workflow.id}, in state {workflow_state}')
            if workflow_state in {States.STARTING, States.ERROR}:
                self.executor.submit(self.wait_for_up, workflow)
            elif workflow_state == States.STOPPING:
                self.executor.submit(self.stop_workflow, workflow)
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

    def probe_all(self):
        ''' Force a health-check rather than waiting for the timer to mature.
        '''
        return [self.probe(workflow_id) for workflow_id in self.probes.keys()]
 
    def probe(self, workflow_id):
        ''' Force a health-check on worfkow_id
        '''
        return {workflow_id : [probe() for probe in self.probes[workflow_id].values()]}

class HealthApp(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = HealthManager()
        self.app.route('/')(self.root_route)
        self.app.route('/probe/<workflow_id>')(self.probe)

    def root_route(self):
        return jsonify({workflow_id: {
            task_id: str(probe)
            for task_id, probe in self.manager.probes[workflow_id].items()
        } for workflow_id in self.manager.workflows.keys()})

    def probe(self, workflow_id):
        if not self.manager.workflows:
            return jsonify({"result":"No workflows exist"})
        if workflow_id == 'all':
            return jsonify( self.manager.probe_all() )
        if workflow_id in self.manager.workflows.keys():
            return jsonify( self.manager.probe(workflow_id) )
        return jsonify({"result":f"Workflow '{workflow_id}' not found"})

    def _shutdown(self):
        self.manager.stop()

    def run_serve(self):
        self.manager.start()
        super().run_serve()


if __name__ == '__main__':
    # Two startup modes:
    # Hot (re)start - Data already exists in etcd, reconstruct probes.
    # Cold start - No workflow and/or probe data are in etcd.
    logging.basicConfig(format=get_log_format('healthd'), level=logging.INFO)
    app = HealthApp(bind='0.0.0.0:5050')
    app.run_serve()
