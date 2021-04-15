import logging
import os.path
import re

from quart import jsonify, request
from ariadne import load_schema_from_path, make_executable_schema
from ariadne.constants import PLAYGROUND_HTML
from ariadne.graphql import graphql_sync

from flowlib.constants import flow_result
from . import bindables, resolvers, mutations, flowd_api
from .async_service import AsyncService
from ariadne import ObjectType

BASEDIR = os.path.dirname(__file__)

flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
flowd_port = os.environ.get('FLOWD_PORT', 9001)
if ':' in flowd_port:
    # inside k8s, FLOWD_PORT has format xxx://xx.xx.xx.xx:xxxx
    # extract the IP and PORT using regex magic
    x = re.search(r'.+://([\d\.]+):(\d+)', flowd_port)
    flowd_host = x.group(1)
    flowd_port = x.group(2)

# the Workflow object (created in init_route)
WORKFLOW_DID = os.environ.get('WORKFLOW_DID','tde-15839350')
assert WORKFLOW_DID is not None, 'WORKFLOW_DID not defined in environment - exiting'

class REXFlowUIBridge(AsyncService):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/ui', methods=['POST'])(self.ui_route)
        self.app.route('/init', methods=['POST'])(self.init_route)
        self.schema = load_schema_from_path(os.path.join(BASEDIR, 'schema'))
        self.graphql_schema = make_executable_schema(
            self.schema,
            bindables.session_id,
            bindables.workflow_id,
            bindables.workflow_type,
            bindables.task_id,
            bindables.state,
            resolvers.query,
            resolvers.workflow_query,
            mutations.mutation,
            mutations.session_mutation,
            mutations.session_state_mutations,
            mutations.workflow_mutations,
            mutations.task_mutations,
        )

        self.workflow = flowd_api.Workflow(WORKFLOW_DID, flowd_host, flowd_port)
        self.workflow.start()

        self.app.route('/graphql', methods=['GET'])(self.graphql_playground)
        self.app.route('/graphql', methods=['POST'])(self.graphql_server)


    def init_route(self, did:str):
        # TODO: When the WF Instance is created, we want the <instance_path>/user_tasks/<user_task_id> to be set to PENDING (or something like that)
        self.etcd.replace(f'{self.get_instance_etcd_key(request)}state', 'pending', 'initialized')
        return {'status': 200, 'message': f'REXFlow UI Bridge assigned to workflow {WORKFLOW_DID}'}

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
