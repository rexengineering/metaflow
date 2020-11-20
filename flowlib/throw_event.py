'''
Implements the BPMNThrowEvent object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
from io import IOBase
import logging
import os
import socket
import subprocess
import sys
from typing import Any, Iterator, List, Mapping, Optional, Set

import yaml
import xmltodict

from .envoy_config import get_envoy_config, Upstream
from .etcd_utils import get_etcd
from .bpmn_util import (
    iter_xmldict_for_key,
    CallProperties,
    ServiceProperties,
    HealthProperties,
    WorkflowProperties,
    BPMNComponent,
    get_annotations
)


Upstream = namedtuple('Upstream', ['name', 'host', 'port', 'path', 'method'])

THROW_GATEWAY_LISTEN_PORT = 5000
THROW_GATEWAY_SVC_PREFIX = "throw"

class BPMNThrowEvent(BPMNComponent):
    '''Wrapper for BPMN service event metadata.
    '''
    def __init__(self, event : OrderedDict, process : OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)

        assert 'queue' in self._annotation, \
            "Must annotate Throw Event with `queue` name (kinesis stream name)."
        assert 'gateway_name' in self._annotation, \
            "Must annotate Throw Event with gateway name (becomes k8s service name)."

        self.queue_name = self._annotation['queue']
        self.name = f"{THROW_GATEWAY_SVC_PREFIX}-{self._annotation['gateway_name']}"
        assert 'service' not in self._annotation, "Service properties auto-inferred for Throw Events."

        self._service_properties.update({
            "port": THROW_GATEWAY_LISTEN_PORT,
            "host": self.name,
        })

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph : OrderedDict) -> list:
        k8s_objects = []

        # k8s ServiceAccount
        service_name = self.service_properties.host
        # FIXME: The following is a workaround; need to add a full-on regex
        # check of the service name and error on invalid spec.
        dns_safe_name = service_name.replace('_', '-')

        port = self.service_properties.port
        service_account = {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {
                'name': dns_safe_name,
            },
        }
        k8s_objects.append(service_account)

        # k8s Service
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': dns_safe_name,
                'labels': {
                    'app': dns_safe_name,
                },
            },
            'spec': {
                'ports': [
                    {
                        'name': 'http',
                        'port': port,
                        'targetPort': port,
                    }
                ],
                'selector': {
                    'app': dns_safe_name,
                },
            },
        }
        k8s_objects.append(service)

        # Here's the tricky part: we need to configure the Environment Variables for the container
        # There are two goals:
        # 1. Tell the container which queue to publish to.
        # 2. Tell the container which (if any) service to forward its input to.
        
        # `targets` should be list of URL's. component_map[foo] returns a BPMNComponent, and
        # BPMNComponent.k8s_url returns the k8s FQDN + http path for the next task.
        targets = [
            component_map[component_id]
            for component_id in digraph.get(self.id, set())
        ]

        assert len(targets) <= 1  # Multiplexing will require a Parallel Gateway.
        target = targets[0] if len(targets) else None

        env_config = [
            {
                "name": "REXFLOW_THROWGATEWAY_QUEUE",
                "value": self.queue_name,
            },
            {
                "name": "REXFLOW_THROWGATEWAY_FORWARD_URL",
                "value": target.k8s_url,
            },
            {
                "name": "REXFLOW_THROWGATEWAY_TOTAL_ATTEMPTS",
                "value": str(target.call_properties.total_attempts) if target else "",
            },

            # We need AWS creds to access boto3. For now, we pass in this janky way (note:
            # we edited the `python -m deploy` to inject these vars to flowd). This is just
            # a temporary hack to enable this until we figure out how to properly get this
            # system on a real DevOps infrastructure.
            {
                "name": "AWS_ACCESS_KEY_ID",
                "value": os.environ["AWS_ACCESS_KEY_ID"]
            },
            {
                "name": "AWS_SECRET_ACCESS_KEY",
                "value": os.environ["AWS_SECRET_ACCESS_KEY"]
            },
        ]

        # k8s Deployment
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': dns_safe_name,
            },
            'spec': {
                'replicas': 1, # FIXME: Make this a property one can set in the BPMN.
                'selector': {
                    'matchLabels': {
                        'app': dns_safe_name,
                    },
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': dns_safe_name,
                        },
                    },
                    'spec': {
                        'serviceAccountName': dns_safe_name,
                        'containers': [
                            {
                                'image': 'throw-gateway:1.0.0',
                                'imagePullPolicy': 'IfNotPresent',
                                'name': dns_safe_name,
                                'ports': [
                                    {
                                        'containerPort': port,
                                    },
                                ],
                                'env': env_config,
                            },
                        ],
                    },
                },
            },
        }
        k8s_objects.append(deployment)

        if self._global_props.namespace is not None:
            service_account['metadata']['namespace'] = self._global_props.namespace
            service['metadata']['namespace'] = self._global_props.namespace
            deployment['metadata']['namespace'] = self._global_props.namespace

        return k8s_objects
