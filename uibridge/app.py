import asyncio
import functools
import hashlib
import json
import logging
import os
import os.path
import requests

from quart import jsonify, request
from ariadne import load_schema_from_path, make_executable_schema
from ariadne.constants import PLAYGROUND_HTML
from ariadne.graphql import graphql_sync

from .prism_api.client import PrismApiClient

from flowlib import executor, user_task
from flowlib.constants import Headers, flow_result, TEST_MODE_URI
from . import graphql_handlers, flowd_api
from .async_service import AsyncService
from .salesforce_utils import SalesforceManager
from uibridge import salesforce_utils


BASEDIR = os.path.dirname(__file__)

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
WORKFLOW_DID = os.environ.get('WORKFLOW_DID')
assert WORKFLOW_DID is not None, 'WORKFLOW_DID not defined in environment - exiting'

BRIDGE_CONFIG = json.loads(os.environ.get('BRIDGE_CONFIG', '{}'))
logging.info(f'My UI bridge configuration is {BRIDGE_CONFIG}')
WORKFLOW_TIDS = list(BRIDGE_CONFIG.keys())
assert len(WORKFLOW_TIDS) > 0, 'Bad BRIDGE_CONFIG defined in environment - exiting'

class REXFlowUIBridge(AsyncService):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.app.route('/', methods=['GET'])(self.healthcheck)
        self.app.route('/task/init', methods=['POST'])(self.init_route)
        self.schema = load_schema_from_path(os.path.join(BASEDIR, 'schema'))
        self.graphql_schema = make_executable_schema(
            self.schema,
            graphql_handlers.query,
            graphql_handlers.mutation,
            graphql_handlers.task_mutation,
        )

        self.workflow = flowd_api.Workflow(WORKFLOW_DID, WORKFLOW_TIDS, BRIDGE_CONFIG, flowd_host, flowd_port)
        # assure salesforce resources exist (if required)
        self.salesforce = os.environ.get('USE_SALESFORCE', 'false').lower() == 'true'
        if self.salesforce:
            # retrieve the salesforce profile from the environment
            sf_profile_json = os.environ.get('SALESFORCE_PROFILE', None)
            assert sf_profile_json is not None, 'Could not retrieve SALESFORCE_PROFILE from environment'
#             sf_profile_json = """{"username":"ghester@rexhomes.com.qa1",
# "consumer_key":"3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk",
# "private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA/USE/o9vB/k6CEPm6sIjcPUiY0rw+jAhRiLJR1wUX9CuJ1+f\\nx/buK0Vqq59cm2bf1eWYIp0J6uqHG8A44xp89oXR6/DmJnJWBi8CRmyjRDNMpnIq\\nVgmjDuFXndKWkyHpyhgVtPIA3Bi+3UHQXbGX8E/rYXea28XQ7/HxybG9YHvJXZhn\\nBwqo8CmUFk+b7mjpwYd4i9cRsVtPDe9Mvf+1VWcGj+bWTAVFTGSjBknzCzJI3Yvh\\nAzhPYK3Zhxi7m/eWEYOPCYPRFxq7gijkaQq2szPYEq20N8r1pWgjXZPmCd/UQ0Ek\\nWHwGYrcmBPirO2/wpJJgQrhbTpMcsZTmw5v5dQIDAQABAoIBAE8TS6rnQbVtnS7j\\ndH+rqcEk6F20ElUrHdh2F/4Nw9a+owFsG8klUet0uv9mvFVQ42Y3Ty7PdT9Bhnml\\npJ1TsdyOn6JZDqLGZBF+L+mpFbi/g5kcYBeI3r5QoTiHfbfmiMYuiuh5/sa5ey49\\n1D7MqjG/4jAGVfV0Z+3izqk4s3Yh0RXU3KbYKVvJlPSAfiRsH8f/IvgIsux8bsCD\\n4+tEg2hBvLLlml9AIHC06S82w/xYBggXje550eMKtERl5bFlk+AIVYTo2bUzpFCX\\nWViv3JC7/6P6E/y6W4xSnaXLlvY+yeKotXkW0XReph/Q1TopI4rzF6VojlmSG3KB\\nCYo+EgECgYEA/8s+j9v54XqBYgozMVq17KcK8NGZFXWJDEeAHNN/DwblSRKTIDRb\\nLQp+H6OP6Rq/jWcQUDp35XwThSw5r6Lsv6Xa0yo2/05c58yCJxNvwIfduIs0emxQ\\nWc4JjP2o/2PbqLVLcFNIjw8jAg7+KGapRs1tC63MXsRQJArMPjsXZsECgYEA/XjB\\nDNgVGvvQK92m7hTCX+nuqx51mOGs1mSdhcCCnjCdwLwHQNQmG4zGPHjFjxeoUx6i\\nuYUFK2b8LJTLjbIWzqTBtiBtfY85XdpjR/SuFncYkHqQ0ms9c5jwA/2qb1IYfIHx\\nGPYov/m5MR3aBPuuPuUzQpwTWV6+HebPHQtwE7UCgYEAgoSSR5VWy1ZW7k+GD4jZ\\niwcw7fAEzI5Mf5d8JzlDe8do9wAjUitk2nagJESxCaA8XUpZaJZs1wuYajtGs/fO\\nFXvrTBQeO+cgQKZ5QrcILpUk7SUagd0CotAez3Ie6TFqw4q+E3Jrc5OlqUc9KCA5\\n/4aSPYNQ5IoG2l0oGhjMuAECgYEAzBgJSfBLvjh4vHlzSk0I3fYdKUgTZJCCfPbz\\nJ5mFEx8ORvyf0oGAVbqafGK6oKdp79PBLyR+rx3ze2osJOH7H1TmbWHbB7jldj68\\nplnMO2aWLu+h4OxcxNGmoXAFZjFyaf6vRWwgD8Ria7wfqteEzDv9dGr74YA6ERWi\\nOz7UdekCgYBslAlmMi8kmtx34GS+STe03xbiO9YtIs2/1qiYF1DQhlpJcDEC/Xtr\\n1UkbKUxLxAL8kL+9onIrUKM8Re3kdA/qFfiLCHpMBhmtUMA0unQQcY2QhXddyzFz\\n7Ts84zwHLQ0QpzTxiWO1j3TBJl59j1arhoB2ecnyT/tsULkR+h9YNQ==\\n-----END RSA PRIVATE KEY-----",
# "domain":"test"}"""
            sf_profile = json.loads(sf_profile_json)
            self._sf_manager = SalesforceManager(self.workflow, sf_profile)
            logging.info(f'Deploying/validating Salesforce resources')
            success, count = self._sf_manager.create_salesforce_assets()
            # success True means the resources exist - the count is the number of resources deployed
            if success:
                self._sf_manager.start()
            else:
                logging.error('Salesforce resources required but do not exist')
                self.salesforce = False
                self._sf_manager = None

        self.workflow.start()

        self.app.route('/graphql', methods=['GET'])(self.graphql_playground)
        self.app.route('/graphql', methods=['POST'])(self.graphql_server)

    def healthcheck(self):
        return jsonify(flow_result(0, "Ok."))

    async def init_route(self):
        '''
        entry point for when the bridge gets called by the rexflow.
        '''
        # TODO: When the WF Instance is created, we want the <instance_path>/user_tasks/<user_task_id> to be set to PENDING (or something like that)
        iid = request.headers[Headers.X_HEADER_FLOW_ID]
        tid = request.headers[Headers.X_HEADER_TASK_ID]
        logging.info(f'Starting init_route()... {iid} {tid}')

        self.etcd.replace(f'{self.get_instance_etcd_key(request)}state', 'pending', 'initialized')
        if Headers.X_HEADER_TOKEN_POOL_ID in request.headers.keys():
            self.workflow.register_instance_header(iid, f'{Headers.X_HEADER_TOKEN_POOL_ID}:{request.headers[Headers.X_HEADER_TOKEN_POOL_ID]}')
        req_json = await request.get_json()
        self.workflow.set_instance_data(iid, req_json)
        ui_srv_url = self.workflow.get_instance_graphql_uri(iid)
        logging.info(req_json)

        # upstream cycle timer events can call this access point multiple times for the
        # same iid/tid pair, so generate a uuid request id (rid) for us to use for this
        # specific interaction
        #rid = hashlib.sha256(request.get_json() + time.now()).hexdigest()[:8]
        if ui_srv_url and not ui_srv_url.startswith(TEST_MODE_URI):
            response = await PrismApiClient.notify_task_started(ui_srv_url, iid, tid)
            logging.info(f'UI-Srv {ui_srv_url} {iid} {tid} {response}')

        return {'status': 200, 'message': f'REXFlow UI Bridge assigned to workflow {WORKFLOW_DID}'}

    async def _happy_path(self, headers, json):
        import requests, functools, asyncio
        logging.info('You have reached the _happy_path() hotline!')

        user_task_id = headers['X-Rexflow-Task-Id']
        assert user_task_id in BRIDGE_CONFIG
        next_tasks = BRIDGE_CONFIG[user_task_id]

        assert len(next_tasks) == 1, "TODO: Handle more than one outbound edge"
        next_task = next_tasks[0]

        try:
            await asyncio.sleep(10)
            my_executor = executor.get_executor()
            loop = asyncio.get_running_loop()
            headers['X-Rexflow-Task-Id'] = next_task['next_task_id_header']
            logging.info(f'headers={headers}')
            call_method = requests.post if next_task['method'] == 'POST' else requests.get
            call = functools.partial(call_method, url=next_task['k8s_url'], headers=headers, json=json)
            result = await loop.run_in_executor(my_executor, call)
            logging.info(f'result={result.ok}')
            logging.info(f'result.headers={result.headers}')
            logging.info(f'result.text={repr(result.text)}')
            result.raise_for_status()
        except Exception as exn:
            logging.exception('Happy path is sad...', exc_info=exn)

    def graphql_playground(self):
        return PLAYGROUND_HTML, 200

    async def graphql_server(self):
        global request
        data = await request.get_json()
        logging.info(request, data)
        context = {
            'request':request, 
            'workflow': self.workflow,
            'salesforce': self.salesforce,
        }
        if self.salesforce:
            context['sf_mgr'] = self._sf_manager
        success, result = graphql_sync(
            self.graphql_schema,
            data,
            context_value = context,
            debug=self.app.debug
        )
        status_code = 200 if success else 400
        return jsonify(result), status_code

    def actual_handler(self, local_request):
        environment = local_request.json()
        # FIXME: The forms shouldn't be a property of the instance, rather they
        # should be a property of the deployment.
        environment.update(self.get_etcd_value(local_request, 'forms'))
        return flow_result(0, 'Ok', **environment)
