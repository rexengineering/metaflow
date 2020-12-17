'''
Implements BPMNStartEvent object, which for now is just a pass-through to Flowd.
'''

from collections import OrderedDict
from typing import Mapping
import os

from .bpmn_util import BPMNComponent

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)


START_EVENT_PREFIX = 'start'
START_EVENT_LISTEN_PORT = '5000'
START_EVENT_CONTAINER = 'catch-gateway:1.0.0'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")


START_EVENT_PREFIX = 'start'
START_EVENT_LISTEN_PORT = '5000'
START_EVENT_CONTAINER = 'catch-gateway:1.0.0'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")


class BPMNStartEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props):
        super().__init__(event, process, global_props)
        self._namespace = global_props.namespace
        self._service_name = f"{START_EVENT_PREFIX}-{self._global_props.id}"
        self._queue = None

        self._service_properties.update({
            'host': self._service_name,
            'port': START_EVENT_LISTEN_PORT,
            'container': START_EVENT_CONTAINER,
        })

        # Check if we listen to a kafka topic to start events.
        if 'queue' in self._annotation:
            self._queue = self._annotation['queue']

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict) -> list:
        assert self._namespace, "new-grad programmer error: namespace should be set by now."

        k8s_objects = []
        dns_safe_name = self.service_properties.host.replace('_', '-')
        port = self.service_properties.port
        namespace = self._namespace

        forward_set = list(digraph.get(self.id, set()))
        assert len(forward_set) == 1
        task = component_map[forward_set[0]]

        deployment_env_config = [
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "REXFLOW_CATCH_START_FUNCTION",
                "value": "START",
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": task.call_properties.total_attempts
            },
            {
                "name": "FORWARD_URL",
                "value": task.k8s_url,
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": dns_safe_name,
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            }
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
