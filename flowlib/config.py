'''Contains the REXFlow configuration. For example, specifies docker
image URL's for various REXFlow containers, and specifies endpoints
for various ancillary services (such as etcd and kafka).

Note: Defaults are provided in this file. HOWEVER, if you deployed
your system via `python -m deploy`, the defaults will be overriden.
See the flowd deployment spec in `deploy/specs.py`.
'''
import os
from pdb import post_mortem

DEFAULT_REXFLOW_ROOT_PREFIX = "/rexflow"
REXFLOW_ROOT_PREFIX = os.getenv('REXFLOW_ROOT_PREFIX', DEFAULT_REXFLOW_ROOT_PREFIX)
if not REXFLOW_ROOT_PREFIX.startswith('/'):
    REXFLOW_ROOT_PREFIX = '/' + REXFLOW_ROOT_PREFIX

# Flowd Endpoints
DEFAULT_FLOWD_HOST = 'localhost'
DEFAULT_FLOWD_PORT = 9002
FLOWD_HOST = os.getenv("REXFLOW_FLOWD_HOST", os.getenv('FLOWD_HOST', DEFAULT_FLOWD_HOST))
FLOWD_PORT = os.getenv('REXFLOW_FLOWD_PORT', os.getenv('FLOWD_PORT', DEFAULT_FLOWD_PORT))
FLOWD_URL = f"http://{FLOWD_HOST}:{FLOWD_PORT}"

INSTANCE_FAIL_ENDPOINT_PATH = "/instancefail"
INSTANCE_FAIL_ENDPOINT = f"{FLOWD_URL}{INSTANCE_FAIL_ENDPOINT_PATH}"

WF_MAP_ENDPOINT_PATH = '/wf_map'
WF_MAP_ENDPOINT = f'{FLOWD_URL}{WF_MAP_ENDPOINT_PATH}'

# Postgres Database Config
DEFAULT_POSTGRES_DB_URI = 'postgresql://postgresadmin:admin123@postgres.rexflow:5432/postgresdb'
POSTGRES_DB_URI = os.getenv('REXFLOW_POSTGRES_DB_URI', DEFAULT_POSTGRES_DB_URI)

# Gateway Configuration
PGATEWAY_SVC_PREFIX = "pgateway"
PGATEWAY_LISTEN_PORT = "5000"


# REXFlow DMN Server Info
DEFAULT_DMN_SERVER_HOST = "http://dmnserver.rexflow:8001"
DMN_SERVER_HOST = os.getenv("REXFLOW_DMN_SERVER_HOST", DEFAULT_DMN_SERVER_HOST)


# REXFlow Docker Image Configuration
DEFAULT_REXFLOW_VERSION = 'latest'
REXFLOW_VERSION = os.getenv('REXFLOW_VERSION', DEFAULT_REXFLOW_VERSION)

DEFAULT_THROW_IMAGE = 'throw-gateway:latest'
THROW_IMAGE = os.getenv('REXFLOW_THROW_IMAGE', DEFAULT_THROW_IMAGE)
if ':' not in THROW_IMAGE:
    THROW_IMAGE += f":{REXFLOW_VERSION}"
DEFAULT_THROW_LISTEN_PORT = '5000'
THROW_LISTEN_PORT = int(os.getenv("REXFLOW_THROW_SERVICE_PORT", DEFAULT_THROW_LISTEN_PORT))

DEFAULT_CATCH_IMAGE = 'catch-gateway:latest'
CATCH_IMAGE = os.getenv('REXFLOW_CATCH_IMAGE', DEFAULT_CATCH_IMAGE)
if ':' not in CATCH_IMAGE:
    CATCH_IMAGE += f":{REXFLOW_VERSION}"
DEFAULT_CATCH_LISTEN_PORT = '5000'
CATCH_LISTEN_PORT = int(os.getenv("REXFLOW_CATCH_SERVICE_PORT", DEFAULT_CATCH_LISTEN_PORT))

DEFAULT_XGW_IMAGE = 'exclusive-gateway:latest'
XGW_IMAGE = os.getenv("REXFLOW_XGW_IMAGE", DEFAULT_XGW_IMAGE)
if ':' not in XGW_IMAGE:
    XGW_IMAGE += f':{REXFLOW_VERSION}'

DEFAULT_PGW_IMAGE = 'parallel-gateway:latest'
PGW_IMAGE = os.getenv("REXFLOW_PGW_IMAGE", DEFAULT_PGW_IMAGE)
if ':' not in PGW_IMAGE:
    PGW_IMAGE += f':{REXFLOW_VERSION}'

DEFAULT_PASSTHROUGH_IMAGE = 'passthrough-container:latest'
PASSTHROUGH_IMAGE = os.getenv("REXFLOW_PASSTHROUGH_IMAGE", DEFAULT_PASSTHROUGH_IMAGE)
if ':' not in PASSTHROUGH_IMAGE:
    PASSTHROUGH_IMAGE += f':{REXFLOW_VERSION}'

DEFAULT_ASYNC_BRIDGE_IMAGE = 'async-bridge:latest'
ASYNC_BRIDGE_IMAGE = os.getenv("REXFLOW_ASYNC_BRIDGE_IMAGE", DEFAULT_ASYNC_BRIDGE_IMAGE)
if ':' not in ASYNC_BRIDGE_IMAGE:
    ASYNC_BRIDGE_IMAGE += f':{REXFLOW_VERSION}'

DEFAULT_ASYNC_BRIDGE_LISTEN_PORT = '5000'
ASYNC_BRIDGE_LISTEN_PORT = int(
    os.getenv('REXFLOW_ASYNC_BRIDGE_LISTEN_PORT', DEFAULT_ASYNC_BRIDGE_LISTEN_PORT)
)

DEFAULT_WORFKLOW_PUBLISHER_IMAGE = 'workflow-publisher:latest'
WORFKLOW_PUBLISHER_IMAGE = os.getenv("REXFLOW_WORKFLOW_PUBLISHER_IMAGE", DEFAULT_WORFKLOW_PUBLISHER_IMAGE)
if ':' not in WORFKLOW_PUBLISHER_IMAGE:
    WORFKLOW_PUBLISHER_IMAGE += f':{REXFLOW_VERSION}'

DEFAULT_WORFKLOW_PUBLISHER_LISTEN_PORT = '5000'
WORKFLOW_PUBLISHER_LISTEN_PORT = int(
    os.getenv('REXFLOW_WORFKLOW_PUBLISHER_LISTEN_PORT', DEFAULT_WORFKLOW_PUBLISHER_LISTEN_PORT)
)

DEFAULT_XGW_LISTEN_PORT = '5000'
XGW_LISTEN_PORT = int(os.getenv("REXFLOW_XGW_LISTEN_PORT", DEFAULT_XGW_LISTEN_PORT))


# Meta-info about the deployment
DEFAULT_CREATE_DEV_INGRESS = "True"
CREATE_DEV_INGRESS = (
    os.getenv("REXFLOW_CREATE_DEV_INGRESS", DEFAULT_CREATE_DEV_INGRESS) == "True"
)

DEFAULT_DO_MANUAL_INJECTION = "True"
DO_MANUAL_INJECTION = (
    os.getenv("REXFLOW_DO_MANUAL_INJECTION", DEFAULT_DO_MANUAL_INJECTION) == "True"
)


# ETCD Configuration
DEFAULT_ETCD_HOST='localhost'
DEFAULT_ETCD_PORT=2379
ETCD_HOST = os.getenv("ETCD_HOST", DEFAULT_ETCD_HOST)  # optional, can get from pods instead
ETCD_PORT = os.getenv("ETCD_PORT", DEFAULT_ETCD_PORT)  # optional, can get from pods instead

ETCD_HOSTS = os.getenv("ETCD_HOSTS", f'{ETCD_HOST}:{ETCD_PORT}')

# Can either provide certs/paths as environment variables or as files, in which
# case the env var is the path to the file. If both are provided, then the
# filepath variable takes precedence.
ETCD_CA_CERT = os.getenv("REXFLOW_ETCD_CA_CERT")
ETCD_CA_CERT_PATH = os.getenv("REXFLOW_ETCD_CA_CERT_PATH")
ETCD_CERT_CERT = os.getenv("REXFLOW_ETCD_CERT_CERT")
ETCD_CERT_CERT_PATH = os.getenv("REXFLOW_ETCD_CERT_CERT_PATH")
ETCD_CERT_KEY = os.getenv("REXFLOW_ETCD_CERT_KEY")
ETCD_CERT_KEY_PATH = os.getenv("REXFLOW_ETCD_CERT_KEY_PATH")


# S3 Bucket, optionally used to store k8s specs.
K8S_SPECS_S3_BUCKET = os.getenv("REXFLOW_K8S_SPECS_S3_BUCKET", None)


# Kafka Configuration (pass-through as configuration to confluent_kafka)
KAFKA_HOST = os.getenv("REXFLOW_KAFKA_HOST", None)
KAFKA_API_KEY = os.getenv("REXFLOW_KAFKA_API_KEY", None)
KAFKA_API_SECRET = os.getenv("REXFLOW_KAFKA_API_SECRET", None)
KAFKA_SASL_MECHANISM = os.getenv("REXFLOW_KAFKA_SASL_MECHANISM", None)
KAFKA_SECURITY_PROTOCOL = os.getenv("REXFLOW_KAFKA_SECURITY_PROTOCOL", None)

kafka_env_map = {
    'bootstrap.servers': KAFKA_HOST,
    'sasl.username': KAFKA_API_KEY,
    'sasl.password': KAFKA_API_SECRET,
    'sasl.mechanism': KAFKA_SASL_MECHANISM,
    'security.protocol': KAFKA_SECURITY_PROTOCOL,
}

def get_kafka_config():
    if KAFKA_HOST is None:
        return None

    return {
        key: kafka_env_map[key] for key in kafka_env_map.keys() if kafka_env_map[key] is not None
    }

DEFAULT_INGRESS = """
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: {name}
  labels:
    cicd.rexhomes.com/deployed-by: rexflow
    rexflow.rexhomes.com/wf-id: {wf_id}
    rexflow.rexhomes.com/component-name: {component_name}
    rexflow.rexhomes.com/component-id: {component_id}
spec:
  rules:
  - host: {hostname}
    http:
      paths:
      - backend:
          serviceName: forward-to-istio
          servicePort: use-annotation
        path: /
        pathType: ImplementationSpecific
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {name}
  labels:
    cicd.rexhomes.com/deployed-by: rexflow
    rexflow.rexhomes.com/wf-id: {wf_id}
    rexflow.rexhomes.com/component-name: {component_name}
    rexflow.rexhomes.com/component-id: {component_id}
spec:
  gateways:
  - {ingress_type}
  hosts:
  - {hostname}
  http:
  - route:
    - destination:
        host: {service_host}
        port:
          number: {service_port}
"""

INGRESS_TEMPLATE = os.getenv("REXFLOW_INGRESS_TEMPLATE", DEFAULT_INGRESS)

# This configuration is pertinent when running the UI bridge.
DEFAULT_UI_BRIDGE_NAME = 'ui-bridge'
UI_BRIDGE_NAME = os.getenv('REXFLOW_UI_BRIDGE_NAME', DEFAULT_UI_BRIDGE_NAME)

DEFAULT_UI_BRIDGE_IMAGE = f'{DEFAULT_UI_BRIDGE_NAME}:latest'
UI_BRIDGE_IMAGE = os.getenv('REXFLOW_UI_BRIDGE_IMAGE', DEFAULT_UI_BRIDGE_IMAGE)

DEFAULT_UI_BRIDGE_PORT=5051
UI_BRIDGE_PORT = int(os.getenv('REXFLOW_UI_BRIDGE_PORT', DEFAULT_UI_BRIDGE_PORT))

DEFAULT_UI_BRIDGE_INIT_PATH = 'task/init'
UI_BRIDGE_INIT_PATH = os.getenv('REXFLOW_UI_BRIDGE_INIT_PATH', DEFAULT_UI_BRIDGE_INIT_PATH)

K8S_DEFAULT_REPLICAS = int(os.getenv('REXFLOW_DEFAULT_K8S_DEPLOYMENT_REPLICAS', '1'))

DEFAULT_USE_PREEXISTING_SERVICES = (
    os.getenv('DEFAULT_USE_PREEXISTING_SERVICES', 'false').lower() == 'true'
)

DEFAULT_NOTIFICATION_KAFKA_TOPIC = os.getenv('DEFAULT_NOTIFICATION_KAFKA_TOPIC')

DEFAULT_USE_CLOSURE_TRANSPORT = (
    os.getenv('DEFAULT_USE_CLOSURE_TRANSPORT', 'false').lower() == 'true'
)

DEFAULT_USE_SHARED_NAMESPACE = (
    os.getenv('DEFAULT_USE_SHARED_NAMESPACE', 'false').lower() == 'true'
)
