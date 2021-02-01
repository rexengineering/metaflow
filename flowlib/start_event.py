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
KAFKA_LISTEN_PORT = '5000'
START_EVENT_CONTAINER = 'catch-gateway:1.0.0'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
ATTEMPTS = 2


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

    def _to_kubernetes_reliable(self, id_hash, component_map: Mapping[str, BPMNComponent],
                                digraph: OrderedDict) -> list:
        '''Sets us up for reliable transport over Kafka.
        '''
        # Two things we need to do:
        # 1. Create the Start Event (which uses the catch-gateway image)
        # 2. Per Hong's design, set up a python daemon that connects the Start Event to the
        # first step in the WF through its designated Kafka topic.

        k8s_objects = []
        start_service_name = self.service_properties.host.replace('_', '-')
        port = self.service_properties.port
        namespace = self._namespace

        forward_set = list(digraph.get(self.id, set()))
        assert len(forward_set) == 1
        next_task = component_map[forward_set[0]]
        throw_service_name = f'{self.id}-{next_task.transport_kafka_topic}'.lower()
        throw_service_name = throw_service_name.replace('_', '-')

        # First, the Start Event.
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
                "value": 2,
            },
            {
                "name": "FORWARD_URL",
                "value": f"http://{throw_service_name}.{self._namespace}:{KAFKA_LISTEN_PORT}/",
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": next_task.id,
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": start_service_name,
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            }
        ]
        if self._queue is not None:
            # We can still start a WF by putting a message into a queue
            deployment_env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._queue,
            })

        k8s_objects.append(create_serviceaccount(namespace, start_service_name))
        k8s_objects.append(create_service(namespace, start_service_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            start_service_name,
            "catch-gateway:1.0.0",
            port,
            deployment_env_config,
        ))
        k8s_objects.append(create_rexflow_ingress_vs(
            namespace,
            start_service_name,
            uri_prefix=f'/{start_service_name}',
            dest_port=port,
            dest_host=f'{start_service_name}.{namespace}.svc.cluster.local',
        ))

        # Now create the daemon to connect Start Event to First Task
        env_config = [
            {
                "name": "KAFKA_TOPIC",
                "value": next_task.transport_kafka_topic,
            },
            {
                "name": "FORWARD_URL",
                "value": None,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": "",
            },
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": '',
            },
        ]

        k8s_objects.append(create_serviceaccount(self._namespace, throw_service_name))
        k8s_objects.append(create_service(self._namespace, throw_service_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            throw_service_name,
            'throw-gateway:1.0.0',
            port,
            env_config,
        ))

        return k8s_objects


    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict) -> list:
        assert self._namespace, "new-grad programmer error: namespace should be set by now."
        if self._global_props._is_reliable_transport:
            return self._to_kubernetes_reliable(id_hash, component_map, digraph)

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
                "name": "FORWARD_TASK_ID",
                "value": task.id,
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
        if self._global_props.traffic_shadow_svc:
            deployment_env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_svc['k8s_url'],
            })

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
