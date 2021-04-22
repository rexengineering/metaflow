import logging
import os
import os.path

from quart import jsonify, request
from ariadne import load_schema_from_path, make_executable_schema
from ariadne.constants import PLAYGROUND_HTML
from ariadne.graphql import graphql_sync

from flowlib import executor
from flowlib.constants import flow_result
from . import graphql_handlers, flowd_api
from .async_service import AsyncService


BASEDIR = os.path.dirname(__file__)
# TODO: Remove this hardcoded endpoint and its uses.
HAPPY_PATH = 'happiness.process-0p1yoqw-aa16211c'

flowd_host = os.environ.get('FLOWD_HOST', 'flowd.rexflow')
env_flowd_port = os.environ.get('FLOWD_PORT', None)
if env_flowd_port is None:
    flowd_port = 9001
elif ':' in env_flowd_port:
    import re
    # inside k8s, FLOWD_PORT has format xxx://xx.xx.xx.xx:xxxx
    # extract the IP and PORT using regex magic
    x = re.search(r'.+://([\d\.]+):(\d+)', env_flowd_port)
    flowd_host = x.group(1)
    flowd_port = int(x.group(2))
else:
    flowd_port = int(env_flowd_port)

logging.info(f'FLOWD address is {flowd_host}:{flowd_port}')

# the Workflow object (created in init_route)
WORKFLOW_DID = os.environ.get('WORKFLOW_DID','tde-15839350')
assert WORKFLOW_DID is not None, 'WORKFLOW_DID not defined in environment - exiting'
WORKFLOW_TIDS = os.environ.get('WORKFLOW_TIDS', '')
assert WORKFLOW_TIDS != '', 'WORKFLOW_TIDS not defined in environment - exiting'

class REXFlowUIBridge(AsyncService):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/ui', methods=['POST'])(self.ui_route)
        self.app.route('/task/init', methods=['POST'])(self.init_route)
        self.schema = load_schema_from_path(os.path.join(BASEDIR, 'schema'))
        self.graphql_schema = make_executable_schema(
            self.schema,
            # bindables.session_id,
            # bindables.workflow_id,
            # bindables.workflow_type,
            # bindables.task_id,
            # bindables.state,
            # resolvers.query,
            # resolvers.workflow_query,
            # mutations.mutation,
            # mutations.session_mutation,
            # mutations.session_state_mutations,
            # mutations.workflow_mutations,
            # mutations.task_mutations,
            graphql_handlers.query,
            graphql_handlers.mutation,
            graphql_handlers.task_mutation,
        )

        self.workflow = flowd_api.Workflow(WORKFLOW_DID, WORKFLOW_TIDS, flowd_host, flowd_port)
        self.workflow.start()

        self.app.route('/graphql', methods=['GET'])(self.graphql_playground)
        self.app.route('/graphql', methods=['POST'])(self.graphql_server)

    async def init_route(self):
        logging.info('Starting init_route()...')
        # TODO: When the WF Instance is created, we want the <instance_path>/user_tasks/<user_task_id> to be set to PENDING (or something like that)
        self.etcd.replace(f'{self.get_instance_etcd_key(request)}state', 'pending', 'initialized')
        import socket, asyncio
        try:
            my_executor = executor.get_executor()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(my_executor, socket.gethostbyname, HAPPY_PATH)
            assert isinstance(result, str)
            json = await request.get_json()
            loop.create_task(self._happy_path(request.headers, json))
            logging.info('Completing init_route() for happy path...')
        except AssertionError as exn:
            logging.exception(
                f'I am seeing a DNS entry for {HAPPY_PATH}, but it is not a string...',
                exc_info=exn
            )
        return {'status': 200, 'message': f'REXFlow UI Bridge assigned to workflow {WORKFLOW_DID}'}

    async def _happy_path(self, headers, json):
        import requests, functools, asyncio
        logging.info('You have reached the _happy_path() hotline!')
        try:
            await asyncio.sleep(10)
            my_executor = executor.get_executor()
            loop = asyncio.get_running_loop()
            headers['X-Rexflow-Task-Id'] = 'Activity_0jtv9s8'
            logging.info(f'headers={headers}')
            get = functools.partial(requests.get, url=f'http://{HAPPY_PATH}', headers=headers, json=json)
            result = await loop.run_in_executor(my_executor, get)
            logging.info(f'result={result.ok}')
            logging.info(f'result.headers={result.headers}')
            logging.info(f'result.text={repr(result.text)}')
            result.raise_for_status()
        except Exception as exn:
            logging.exception('Happy path is sad...', exc_info=exn)

    def ui_route(self):
        state = self.get_state_from_etcd(request)  # Gets ID from request...
        command = self.get_command_from_request(request)

        # TODO: allow for more flexible state transitions, including multiple SAVE's
        # or potentially a CANCEL.
        if (state, command) == ('initialized', 'forms'):
            return self.get_forms(request)
        elif (state, command) == ('forms_sent', 'save'):
            return self.save_forms(request)
        elif (state, command) == ('forms_saved', 'validate'):
            return self.validate_forms(request)
        elif (state, command) == ('validated', 'complete'):
            return self.completed(request)
        return self.handle_error(request)

    def graphql_playground(self):
        return PLAYGROUND_HTML, 200

    async def graphql_server(self):
        global request
        data = await request.get_json()
        logging.info(request, data)
        success, result = graphql_sync(
            self.graphql_schema,
            data,
            context_value = {'request':request, 'workflow': self.workflow},
            debug=self.app.debug
        )
        status_code = 200 if success else 400
        return jsonify(result), status_code

    def get_state_from_etcd(self, request):
        raise NotImplementedError('Lazy developer error!')

    def get_command_from_request(self, request):
        raise NotImplementedError('Lazy developer error!')

    def get_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def save_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def validate_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def completed(self, request):
        raise NotImplementedError('Lazy developer error!')

    def handle_error(self, request):
        return flow_result(-1, 'Error: Invalid command!')

    def get_callback(self, request):
        '''Can return one of the 4 verbs: Forms/save/validate/complete
        '''
        pass

    def actual_handler(self, local_request):
        environment = local_request.json()
        # FIXME: The forms shouldn't be a property of the instance, rather they
        # should be a property of the deployment.
        environment.update(self.get_etcd_value(local_request, 'forms'))
        return flow_result(0, 'Ok', **environment)
