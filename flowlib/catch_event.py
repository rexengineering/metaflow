"""
Implements the BPMNCatchEvent object, which inherits BPMNComponent.
"""

from collections import OrderedDict
from flowlib.timer_util import TimedEventManager, ValidationResults
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
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
    INSTANCE_FAIL_ENDPOINT,
    K8S_DEFAULT_REPLICAS,
)
from .reliable_wf_utils import create_kafka_transport
from .constants import BPMN_MESSAGE_EVENT_DEFINITION

CATCH_GATEWAY_SVC_PREFIX = "catch"


class BPMNCatchEvent(BPMNComponent):
    MAX_RECURRANCE = 1024
    """Wrapper for BPMN service event metadata.
    """
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(event, process, global_props)
        self._kafka_topic = None
        self._correlation = None
        self._catch_event_expiration = global_props.catch_event_expiration

        # if this is a timed catch event, verify that the timer aspects are valid
        if self._is_timer:
            # dynamic timer specifications contain substitutions and/or functions, so the validation
            # actually happens in-context when the timer is created by the wf.
            if not self._timer_dynamic and self._timer_aspects is not None and self._timer_aspects.is_cycle:
                aspects:ValidationResults = self._timer_aspects
                assert aspects.recurrence > aspects.UNBOUNDED, f'Unbounded recurrence is not allowed for timed catch events'
                assert aspects.recurrence <= self.MAX_RECURRANCE, f'Recurrance must be between 1 and {self.MAX_RECURRANCE}, inclusive'
        else:
            if BPMN_MESSAGE_EVENT_DEFINITION not in event:
                raise ValueError(
                    f"Catch event {self.id} is neither timer nor message catch event.")

            if (self._annotation is None or
                'topic' not in self._annotation or
                'correlation' not in self._annotation
            ):
                raise ValueError(
                    "Until REXFlow writes its own modeler, you must annotate catch " + \
                    "events with `topic` and `correlation`."
                )

            self._kafka_topic = self._annotation['topic']
            self.kafka_topics.append(self._kafka_topic)
            self._correlation = self._annotation['correlation']
            if 'catch_event_expiration' in self._annotation:
                self._catch_event_expiration = self._annotation['catch_event_expiration']

        self._service_properties.update({
            "host": self.name,
            "port": CATCH_LISTEN_PORT,
        })

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
        assert self._timer_aspects is not None or self._timer_dynamic or KAFKA_HOST is not None, \
            "Kafka Installation required for Catch Events."

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

        env_config = self.init_env_config() + \
        [
            {
                "name": "KAFKA_GROUP_ID",
                "value": f'rexflow_{service_name}',
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
                "name": "REXFLOW_CATCH_EVENT_CORRELATION",
                "value": self._correlation,
            },
            {
                "name": "TID",
                "value": self.id,
            },
            {
                "name": "CATCH_EVENT_EXPIRATION",
                "value": str(self._catch_event_expiration),
            }
        ]
        if self._kafka_topic is not None:
            env_config.append({
                "name": "KAFKA_TOPIC",  # Topic which starts the wf, NOT reliable transport topic
                "value": self._kafka_topic,
            })

        k8s_objects.append(create_serviceaccount(self._namespace, service_name))
        k8s_objects.append(create_service(self._namespace, service_name, port))
        if self._timer_aspects or self._timer_dynamic:
            replicas = 1
        else:
            replicas = K8S_DEFAULT_REPLICAS
        k8s_objects.append(create_deployment(
            self._namespace,
            service_name,
            CATCH_IMAGE,
            CATCH_LISTEN_PORT,
            env_config,
            kafka_access=True,
            etcd_access=True,
            priority_class=self.workflow_properties.priority_class,
            health_props=self.health_properties,
            replicas=replicas,
        ))
        return k8s_objects
