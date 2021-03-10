'''
Implements the BPMNCatchEvent object, which inherits BPMNComponent.
'''

from collections import OrderedDict
from typing import Mapping
import os

from .bpmn_util import BPMNComponent, WorkflowProperties, get_edge_transport

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_deployment_affinity,
)
from .config import (
    ETCD_HOST,
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
    INSTANCE_FAIL_ENDPOINT,
)
from .reliable_wf_utils import create_kafka_transport

CATCH_GATEWAY_SVC_PREFIX = "catch"


class BPMNCatchEvent(BPMNComponent):
    '''Wrapper for BPMN service event metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)

        assert 'kafka_topic' in self._annotation, \
            "Must annotate Catch Event with `kafka_topic` name."

        self._kafka_topic = self._annotation['kafka_topic']
        self.kafka_topics.append(self._kafka_topic)

        assert 'service' not in self._annotation, \
            "Service Properties auto-inferred for Catch Gateways."

        self._service_properties.update({
            "host": self.name,
            "port": CATCH_LISTEN_PORT,
        })

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
        assert KAFKA_HOST is not None, "Kafka Installation required for Catch Events."

        k8s_objects = []
        total_attempts = None
        target_url = None
        task_id = None

        outgoing_edges = list(edge_map[self.id])
        assert len(outgoing_edges) == 1, "Catch Event must have excactly one outgoing edge."
        edge = outgoing_edges[0]
        transport_type = get_edge_transport(edge, self.workflow_properties.transport)
        assert edge['@sourceRef'] == self.id, "Got an invalid edge map."
        next_task = component_map[edge['@targetRef']]

        if transport_type == 'kafka':
            transport = create_kafka_transport(self, next_task)
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

        env_config = [
            {
                "name": "KAFKA_HOST",
                "value": KAFKA_HOST,
            },
            {
                "name": "KAFKA_TOPIC",  # Topic which starts the wf, NOT reliable transport topic
                "value": self._kafka_topic,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": service_name,
            },
            {
                "name": "FORWARD_URL",
                "value": target_url,
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": task_id,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": str(total_attempts),
            },
            {
                "name": "FAIL_URL",
                "value": INSTANCE_FAIL_ENDPOINT,
            },
            {
                "name": "ETCD_HOST",
                "value": ETCD_HOST,
            },
        ]

        k8s_objects.append(create_serviceaccount(self._namespace, service_name))
        k8s_objects.append(create_service(self._namespace, service_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            service_name,
            CATCH_IMAGE,
            CATCH_LISTEN_PORT,
            env_config,
        ))
        return k8s_objects
