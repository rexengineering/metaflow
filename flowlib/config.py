'''Contains the REXFlow configuration. For example, specifies docker
image URL's for various REXFlow containers, and specifies endpoints
for various ancillary services (such as etcd and kafka).

Note: Defaults are provided in this file. HOWEVER, if you deployed
your system via `python -m deploy`, the defaults will be overriden.
See the flowd deployment spec in `deploy/specs.py`.
'''
import os

REXFLOW_VERSION = os.getenv('REXFLOW_VERSION', '1.0.0')

THROW_IMAGE = os.getenv('REXFLOW_THROW_IMAGE', 'throw-gateway:1.0.0')
if ':' not in THROW_IMAGE:
    THROW_IMAGE += f":{REXFLOW_VERSION}"
THROW_LISTEN_PORT = int(os.getenv("REXFLOW_THROW_SERVICE_PORT", '5000'))

CATCH_IMAGE = os.getenv('REXFLOW_CATCH_IMAGE', 'catch-gateway:1.0.0')
if ':' not in CATCH_IMAGE:
    CATCH_IMAGE += f":{REXFLOW_VERSION}"
CATCH_LISTEN_PORT = int(os.getenv("REXFLOW_CATCH_SERVICE_PORT", '5000'))

XGW_IMAGE = os.getenv("REXFLOW_XGW_IMAGE", "exclusive-gateway:1.0.0")
if ':' not in XGW_IMAGE:
    XGW_IMAGE += f':{REXFLOW_VERSION}'
XGW_LISTEN_PORT = int(os.getenv("REXFLOW_XGW_LISTEN_PORT", '5000'))

DMN_SERVER_URL = os.getenv("REWXFLOW_DMN_SERVER_HOST", "http://dmnserver.rexflow:8001")

KAFKA_HOST = os.getenv("KAFKA_HOST", None)

ETCD_HOST = os.environ["ETCD_HOST"]  # Fail if no etcd host specified.

IS_PRODUCTION = (os.getenv("REXFLOW_IS_PRODUCTION") == "True")
