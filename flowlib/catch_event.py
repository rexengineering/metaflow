'''
Implements the BPMNCatchEvent object, which inherits BPMNComponent.
'''

from collections import OrderedDict
from typing import Mapping
import os

from .bpmn_util import BPMNComponent, WorkflowProperties

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_deployment_affinity,
)
from .config import (
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
)

CATCH_GATEWAY_SVC_PREFIX = "catch"


class BPMNCatchEvent(BPMNComponent):
    '''Wrapper for BPMN service event metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)

        assert 'queue' in self._annotation, \
            "Must annotate Catch Event with `queue` name (kinesis stream name)."
        assert 'gateway_name' in self._annotation, \
            "Must annotate Catch Event with gateway name (becomes k8s service name)."

        self.queue_name = self._annotation['queue']
        self.kafka_topics.append(self.queue_name)

        # We've got the annotation. From here, let's find out the name of the resulting
        # gateway service.
        self.name = f"{CATCH_GATEWAY_SVC_PREFIX}-{self._annotation['gateway_name']}"
        assert 'service' not in self._annotation, \
            "Service Properties auto-inferred for Catch Gateways."

        self._service_properties.update({
            "host": self.name,
            "port": CATCH_LISTEN_PORT,
        })

    def _to_kubernetes_reliable(self, id_hash, component_map: Mapping[str, BPMNComponent],
                                digraph: OrderedDict) -> list:
        assert KAFKA_HOST is not None, "Kafka Installation required for reliable WF."
        k8s_objects = []
        # Two things to do:
        # 1. The Special Kafka Transport Pod, which then fires an event to the Kafka
        # topic of the next pod.
        # 2. The standard Catch Event (almost as below, but not quite, since it targets
        # the special Kafka transport pod rather than to the next step in the wf)

        # Step 1: The Special Kafka Transport Pod
        targets = [
            component_map[component_id]
            for component_id in digraph.get(self.id, set())
        ]

        assert len(targets) <= 1  # Multiplexing will require a Parallel Gateway.
        target = targets[0] if len(targets) else None
        throw_service_name = f'{self.id}-{target.transport_kafka_topic}'.lower().replace('_', '-')

        env_config = [
            {
                "name": "KAFKA_TOPIC",
                "value": target.transport_kafka_topic,
            },
            {
                "name": "FORWARD_URL",
                "value": '',
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
                "value": target.id,
            },
        ]
        k8s_objects.append(create_serviceaccount(self._namespace, throw_service_name))
        k8s_objects.append(create_service(self._namespace, throw_service_name, THROW_LISTEN_PORT))
        deployment = create_deployment(
            self._namespace,
            throw_service_name,
            THROW_IMAGE,
            THROW_LISTEN_PORT,
            env_config,
        )
        # The name for the actual Start Event
        dns_safe_name = self.service_properties.host.replace('_', '-')
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            dns_safe_name,
            throw_service_name,
        )

        k8s_objects.append(deployment)

        # Step 2: The normal Catch Event...but it forwards to the special thing we wrote above.
        env_config = [
            {
                "name": "KAFKA_HOST",
                "value": KAFKA_HOST,
            },
            {
                "name": "KAFKA_TOPIC",
                "value": self.queue_name,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": self.id,
            },
            {
                "name": "FORWARD_URL",
                "value": f"http://{throw_service_name}.{self._namespace}:{THROW_LISTEN_PORT}/",
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": self.id,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": "2",
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            },
        ]
        if self._global_props.traffic_shadow_svc:
            env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_svc['k8s_url'],
            })
        dns_safe_name = self.service_properties.host.replace('_', '-')
        k8s_objects.append(create_serviceaccount(self._namespace, dns_safe_name))
        k8s_objects.append(create_service(self._namespace, dns_safe_name, CATCH_LISTEN_PORT))
        k8s_objects.append(create_deployment(
            self._namespace,
            dns_safe_name,
            CATCH_IMAGE,
            CATCH_LISTEN_PORT,
            env_config,
        ))

        return k8s_objects

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict) -> list:
        assert KAFKA_HOST is not None, "Kafka Installation required for Catch Events."
        if self._global_props._is_reliable_transport:
            return self._to_kubernetes_reliable(id_hash, component_map, digraph)

        k8s_objects = []

        # k8s ServiceAccount
        service_name = self.service_properties.host
        # FIXME: The following is a workaround; need to add a full-on regex
        # check of the service name and error on invalid spec.
        dns_safe_name = service_name.replace('_', '-')
        port = self.service_properties.port

        # Here's the tricky part: we need to configure the Environment Variables for the container
        # There are two goals:
        # 1. Tell the container which queue to publish to.
        # 2. Tell the container which (if any) service to forward its input to.

        # `targets` should be list of URL's. component_map[foo] returns a BPMNComponent, and
        # BPMNComponent.k8s_url() returns the k8s FQDN + http path for the next task.
        targets = [
            component_map[component_id]
            for component_id in digraph.get(self.id, set())
        ]

        assert len(targets) <= 1  # Multiplexing will require a Parallel Gateway.
        target = targets[0] if len(targets) else ''
        env_config = [
            {
                "name": "KAFKA_HOST",
                "value": KAFKA_HOST,
            },
            {
                "name": "KAFKA_TOPIC",
                "value": self.queue_name,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": dns_safe_name,
            },
            {
                "name": "FORWARD_URL",
                "value": target.k8s_url,
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": target.id,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": str(target.call_properties.total_attempts) if target else "2",
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            },
        ]

        k8s_objects.append(create_serviceaccount(self._namespace, dns_safe_name))
        k8s_objects.append(create_service(self._namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            dns_safe_name,
            CATCH_IMAGE,
            CATCH_LISTEN_PORT,
            env_config,
        ))
        return k8s_objects
