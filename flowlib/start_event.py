'''
Implements BPMNStartEvent object, which for now is just a pass-through to Flowd.
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
    BPMNComponent,
)


START_EVENT_PREFIX = 'start'
START_EVENT_CONTAINER = 'catch-gateway:1.0.0'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
LISTEN_PORT = 5000


class BPMNStartEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict, global_props):
        # Note: We don't call the super constructor.
        # TODO: separate this code out from Flowd
        self._namespace = global_props.namespace
        self._id = global_props.id
        self._kafka_topic = None

        self._service_name = f"{START_EVENT_PREFIX}-{self._id.replace('_', '-')}"
        self.service_properties.update({
            'host': self._service_name,
            'container': START_EVENT_CONTAINER,
            'port': LISTEN_PORT,
        })

        # Can start a WF Instance by pushing event to a queue.
        if 'kafka_topic' in self._annotation:
            self._kafka_topic = self._annotation['kafka_topic']

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph : OrderedDict) -> list:
        k8s_objects = []
        dns_safe_name = self.service_properties.host.replace('_', '-')
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

        targets = [
            component_map[component_id]
            for component_id in digraph.get(self.id, set())
        ]

        assert len(targets) == 1, "There must be one direct call from Start Event."
        target = targets[0]

        # Due to similarities with the Catch-Gateway Container, we will use the same docker
        # container but configure differently with environment variables.
        env_config = [
            {
                "name": "REXFLOW_CATCHGATEWAY_KAFKA_HOST",
                "value": KAFKA_HOST,
            },
            {
                "name": "REXFLOW_CATCHGATEWAY_KAFKA_TOPIC",
                "value": self._kafka_topic,
            },
            {
                "name": "REXFLOW_CATCHGATEWAY_KAFKA_GROUP_ID",
                "value": dns_safe_name,
            },
            {
                "name": "REXFLOW_CATCHGATEWAY_FORWARD_URL",
                "value": target.k8s_url,
            },
            {
                "name": "REXFLOW_CATCHGATEWAY_TOTAL_ATTEMPTS",
                "value": str(target.call_properties.total_attempts),
            },
            {
                "name": "REXFLOW_CATCHGATEWAY_FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            # Now for the actual configuration
            {
                "name": "REXFLOW_CATCH_START_FUNCTION",
                "value": "START_EVENT",
            },
            {
                "name": "REXFLOW_WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "WF_INSTANCE_STATE_KEY",
                "value": WF_INSTANCE_STATE_KEY,
            },
            {
                "name": "WF_INSTANCE_JAEGER_KEY",
                "value": WF_INSTANCE_JAEGER_KEY,
            }
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
                                'image': 'catch-gateway:1.0.0',
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
            service_account['metadata']['namespace'] = self._namespace
            service['metadata']['namespace'] = self._namespace
            deployment['metadata']['namespace'] = self._namespace

