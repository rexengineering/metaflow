'''Contains the REXFlow configuration. For example, specifies docker
image URL's for various REXFlow containers, and specifies endpoints
for various ancillary services (such as etcd and kafka).

Note: Defaults are provided in this file. HOWEVER, if you deployed
your system via `python -m deploy`, the defaults will be overriden.
See the flowd deployment spec in `deploy/specs.py`.
'''
import os

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

DEFAULT_DMN_SERVER_URL = "http://dmnserver.rexflow:8001"
DMN_SERVER_URL = os.getenv("REWXFLOW_DMN_SERVER_HOST", DEFAULT_DMN_SERVER_URL)

# Kafka is not required.
KAFKA_HOST = os.getenv("KAFKA_HOST", None)

IS_PRODUCTION = (os.getenv("REXFLOW_IS_PRODUCTION") == "True")

ETCD_HOST = os.getenv("ETCD_HOST")
if IS_PRODUCTION:
    assert ETCD_HOST is not None