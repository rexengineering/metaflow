'''Contains the REXFlow configuration. For example, specifies docker
image URL's for various REXFlow containers, and specifies endpoints
for various ancillary services (such as etcd and kafka).

Note: Defaults are provided in this file. HOWEVER, if you deployed
your system via `python -m deploy`, the defaults will be overriden.
See the flowd deployment spec in `deploy/specs.py`.
'''
import os


# Flowd Endpoints
DEFAULT_FLOWD_HOST = 'flowd.rexflow:9002'
FLOWD_HOST = os.getenv("REXFLOW_FLOWD_HOST", DEFAULT_FLOWD_HOST)
FLOWD_URL = f"http://{FLOWD_HOST}"

INSTANCE_FAIL_ENDPOINT_PATH = "/instancefail"
INSTANCE_FAIL_ENDPOINT = f"{FLOWD_URL}{INSTANCE_FAIL_ENDPOINT_PATH}"

LIST_ETCD_HOSTS_ENDPOINT_PATH = '/etcd_hosts'
LIST_ETCD_HOSTS_ENDPOINT = f"{FLOWD_URL}{LIST_ETCD_HOSTS_ENDPOINT_PATH}"


# Gateway Configuration
PGATEWAY_SVC_PREFIX = "pgateway"
PGATEWAY_LISTEN_PORT = "5000"


# REXFlow DMN Server Info
DEFAULT_DMN_SERVER_HOST = "http://dmnserver.rexflow:8001"
DMN_SERVER_HOST = os.getenv("REXFLOW_DMN_SERVER_HOST", DEFAULT_DMN_SERVER_HOST)


# REXFlow Docker Image Configuration
DEFAULT_REXFLOW_VERSION = '1.0.0'
REXFLOW_VERSION = os.getenv('REXFLOW_VERSION', DEFAULT_REXFLOW_VERSION)

DEFAULT_THROW_IMAGE = 'throw-gateway:1.0.0'
THROW_IMAGE = os.getenv('REXFLOW_THROW_IMAGE', DEFAULT_THROW_IMAGE)
if ':' not in THROW_IMAGE:
    THROW_IMAGE += f":{REXFLOW_VERSION}"
DEFAULT_THROW_LISTEN_PORT = '5000'
THROW_LISTEN_PORT = int(os.getenv("REXFLOW_THROW_SERVICE_PORT", DEFAULT_THROW_LISTEN_PORT))

DEFAULT_CATCH_IMAGE = 'catch-gateway:1.0.0'
CATCH_IMAGE = os.getenv('REXFLOW_CATCH_IMAGE', DEFAULT_CATCH_IMAGE)
if ':' not in CATCH_IMAGE:
    CATCH_IMAGE += f":{REXFLOW_VERSION}"
DEFAULT_CATCH_LISTEN_PORT = '5000'
CATCH_LISTEN_PORT = int(os.getenv("REXFLOW_CATCH_SERVICE_PORT", DEFAULT_CATCH_LISTEN_PORT))

DEFAULT_XGW_IMAGE = 'exclusive-gateway:1.0.0'
XGW_IMAGE = os.getenv("REXFLOW_XGW_IMAGE", DEFAULT_XGW_IMAGE)
if ':' not in XGW_IMAGE:
    XGW_IMAGE += f':{REXFLOW_VERSION}'

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
I_AM_FLOWD = True if os.getenv("I_AM_FLOWD") == "True" else False


# ETCD Configuration
ETCD_HOST = os.getenv("ETCD_HOST")  # optional, can get from pods instead
ETCD_PORT = os.getenv("ETCD_PORT")  # optional, can get from pods instead
# Allows REXFlow to get dynamically-changing etcd hosts by kubectl describing
# some pods according to a label.
ETCD_POD_LABEL_SELECTOR = os.getenv("REXFLOW_ETCD_POD_LABEL_SELECTOR")

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

INGRESS_TEMPLATE = os.getenv("REXFLOW_INGRESS_TEMPLATE")
