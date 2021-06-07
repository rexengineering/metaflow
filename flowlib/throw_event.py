'''
Implements the BPMNThrowEvent object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
import os
from typing import Mapping

from .bpmn_util import WorkflowProperties, BPMNComponent, get_edge_transport
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
from .reliable_wf_utils import create_kafka_transport

Upstream = namedtuple('Upstream', ['name', 'host', 'port', 'path', 'method'])

THROW_GATEWAY_SVC_PREFIX = "throw"


class BPMNThrowEvent(BPMNComponent):
    '''Wrapper for BPMN service event metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)

        assert 'service' not in self._annotation, "Service properties auto-inferred for Throw Event"
        assert 'kafka_topic' in self._annotation, \
            "Must annotate Throw Event with `kafka_topic` name."

        self._kafka_topic = self._annotation['kafka_topic']
        self._kafka_topics.append(self._kafka_topic)

        self._service_properties.update({
            "port": THROW_LISTEN_PORT,
            "host": self.name,
        })

    def to_kubernetes(self,
                      id_hash,
                      component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict,
                      edge_map: OrderedDict) -> list:
        assert KAFKA_HOST is not None, "Kafka Installation required for Throw Events."

        k8s_objects = []
        total_attempts = ''
        target_url = ''
        task_id = ''

        outgoing_edges = list(edge_map.get(self.id, set()))
        assert len(outgoing_edges) <= 1, "Throw Event must have zero or one outgoing edges."
        if len(outgoing_edges):
            edge = outgoing_edges[0]
            transport_type = get_edge_transport(edge, self.workflow_properties.transport)
            assert edge['@sourceRef'] == self.id, "Got an invalid edge map."
            next_task = component_map[edge['@targetRef']]

            if transport_type == 'kafka':
                transport = create_kafka_transport(self, next_task)
                self.kafka_topics.append(transport.kafka_topic)
                target_url = f'http://{transport.envoy_host}:{transport.port}{transport.path}'
                task_id = self.id
                total_attempts = transport.total_attempts
                k8s_objects.extend(transport.k8s_specs)
            elif transport_type == 'rpc':
                target_url = next_task.k8s_url
                total_attempts = next_task.call_properties.total_attempts
                task_id = next_task.id
            else:
                assert False, f"Transport '{transport_type}' is not implemented."

        # k8s ServiceAccount
        service_name = self.service_name
        # FIXME: The following is a workaround; need to add a full-on regex
        # check of the service name and error on invalid spec.

        port = self.service_properties.port

        # Here's the tricky part: we need to configure the Environment Variables for the container
        # There are two goals:
        # 1. Tell the container which queue to publish to.
        # 2. Tell the container which (if any) service to forward its input to.

        env_config = self.init_env_config() + \
        [
            {
                "name": "KAFKA_TOPIC",  # Topic to publish to, NOT Reliable Transport topic
                "value": self._kafka_topic,
            },
            {
                "name": "FORWARD_URL",
                "value": target_url,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": str(total_attempts),
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": task_id,
            },
        ]
        if self._global_props.traffic_shadow_url:
            env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_url,
            })

        k8s_objects.append(create_serviceaccount(self._namespace, service_name))
        k8s_objects.append(create_service(self._namespace, service_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            service_name,
            THROW_IMAGE,
            THROW_LISTEN_PORT,
            env_config,
            kafka_access=True,
            priority_class=self.workflow_properties.priority_class,
            health_props=self.health_properties,
        ))

        return k8s_objects
