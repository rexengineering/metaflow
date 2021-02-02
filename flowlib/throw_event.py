'''
Implements the BPMNThrowEvent object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
import os
from typing import Mapping

from .bpmn_util import WorkflowProperties, BPMNComponent
from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_deployment_affinity,
)

Upstream = namedtuple('Upstream', ['name', 'host', 'port', 'path', 'method'])

THROW_GATEWAY_LISTEN_PORT = 5000
THROW_GATEWAY_SVC_PREFIX = "throw"
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
KAFKA_LISTEN_PORT = 5000


class BPMNThrowEvent(BPMNComponent):
    '''Wrapper for BPMN service event metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)

        assert 'queue' in self._annotation, \
            "Must annotate Throw Event with `queue` name (kinesis stream name)."
        assert 'gateway_name' in self._annotation, \
            "Must annotate Throw Event with gateway name (becomes k8s service name)."

        self.queue_name = self._annotation['queue']
        self._kafka_topics.append(self.queue_name)
        self.name = f"{THROW_GATEWAY_SVC_PREFIX}-{self._annotation['gateway_name']}"
        assert 'service' not in self._annotation, "Service properties auto-inferred for Throw Event"

        self._service_properties.update({
            "port": THROW_GATEWAY_LISTEN_PORT,
            "host": self.name,
        })

    def _generate_reliable_kafka_catcher(self, component_map, digraph, throw_svc):
        k8s_objects = []
        env_config = [
            {
                "name": "KAFKA_HOST",
                "value": KAFKA_HOST,
            },
            {
                "name": "KAFKA_TOPIC",
                "value": self.transport_kafka_topic,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": self.id,
            },
            {
                "name": "FORWARD_URL",
                "value": self.k8s_url,
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
        catch_daemon_name = f'{self.id}-{self.transport_kafka_topic}'.lower().replace('_', '-')

        k8s_objects.append(create_serviceaccount(self._namespace, catch_daemon_name))
        k8s_objects.append(create_service(self._namespace, catch_daemon_name, KAFKA_LISTEN_PORT))
        deployment = create_deployment(
            self._namespace,
            catch_daemon_name,
            'catch-gateway:1.0.0',
            KAFKA_LISTEN_PORT,
            env_config,
        )
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            self.service_properties.host.replace('_', '-'),
            catch_daemon_name,
        )
        k8s_objects.append(deployment)
        return k8s_objects

    def to_kubernetes(self,
                      id_hash,
                      component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict) -> list:
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
        # BPMNComponent.k8s_url returns the k8s FQDN + http path for the next task.
        targets = [
            component_map[component_id]
            for component_id in digraph.get(self.id, set())
        ]

        assert len(targets) <= 1  # Multiplexing will require a Parallel Gateway.
        target = targets[0] if len(targets) else None

        env_config = [
            {
                "name": "KAFKA_TOPIC",
                "value": self.queue_name,
            },
            {
                "name": "FORWARD_URL",
                "value": target.k8s_url if target else None,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": str(target.call_properties.total_attempts) if target else "",
            },
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": target.id if target else '',
            },
        ]
        if self._global_props.traffic_shadow_svc:
            env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_svc['k8s_url'],
            })

        k8s_objects.append(create_serviceaccount(self._namespace, dns_safe_name))
        k8s_objects.append(create_service(self._namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            dns_safe_name,
            'throw-gateway:1.0.0',
            port,
            env_config,
        ))

        if self._global_props._is_reliable_transport:
            k8s_objects.extend(
                self._generate_reliable_kafka_catcher(component_map, digraph, dns_safe_name)
            )

        return k8s_objects
