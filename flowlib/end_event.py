'''
Implements BPMNEndEvent object, which for now is just a pass-through to Flowd.
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

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)

END_EVENT_PREFIX = 'end'
END_EVENT_LISTEN_PORT = '5000'
END_EVENT_CONTAINER = 'throw-gateway:1.0.0'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")


class BPMNEndEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, event : OrderedDict, process : OrderedDict, global_props):
        super().__init__(event, process, global_props)
        self._namespace = global_props.namespace
        assert 'service' in self._annotation, "Must provide service host annotation for all End Events."
        assert 'host' in self._annotation['service'], "Must provide service host annotation for all End Events."
        assert 'port' not in self._annotation['service'], "End Event Service Port is auto-configured."

        self._service_name = f"{END_EVENT_PREFIX}-{self._annotation['service']['host']}"
        self._queue = None

        self._service_properties.update({
            'host': self._service_name,
            'port': END_EVENT_LISTEN_PORT,
            'container': END_EVENT_CONTAINER,
        })

        # Check if we listen to a kafka topic to start events.
        if 'queue' in self._annotation:
            self._queue = self._annotation['queue']

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph : OrderedDict) -> list:
        assert self._namespace, "new-grad programmer error: namespace should be set by now."

        k8s_objects = []
        dns_safe_name = self.service_properties.host.replace('_', '-')
        port = self.service_properties.port
        namespace = self._namespace

        forward_set = list(digraph.get(self.id, set()))
        assert len(forward_set) == 0

        deployment_env_config = [
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "REXFLOW_THROW_END_FUNCTION",
                "value": "END",
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "FORWARD_URL",
                "value": None,
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            },
            {
                "name": "END_EVENT_NAME",
                "value": self._service_name,
            },
        ]
        if self._queue is not None:
            deployment_env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._queue,
            })

        k8s_objects.append(create_serviceaccount(namespace, dns_safe_name))
        k8s_objects.append(create_service(namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            dns_safe_name,
            self.service_properties.container,
            port,
            deployment_env_config,
        ))
        k8s_objects.append(create_rexflow_ingress_vs(
            namespace,
            dns_safe_name,
            uri_prefix=f'/{dns_safe_name}',
            dest_port=port,
            dest_host=f'{dns_safe_name}.{namespace}.svc.cluster.local',
        ))
        return k8s_objects
