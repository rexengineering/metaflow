'''
Implements BPMNStartEvent object, which for now is just a pass-through to Flowd.
'''

from collections import OrderedDict
from typing import Mapping
import os

from .bpmn_util import BPMNComponent, get_edge_transport
from .constants import to_valid_k8s_name

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)
from .reliable_wf_utils import create_kafka_transport

from .config import (
    KAFKA_HOST,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
    CREATE_DEV_INGRESS,
    FLOWD_HOST,
    FLOWD_PORT,
)


START_EVENT_PREFIX = 'start'
ATTEMPTS = 2


class BPMNStartEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props):
        super().__init__(event, process, global_props)
        self._namespace = global_props.namespace

        # Just for the Start Event, if the user specifies no name on BPMN, we will
        # provide a somewhat readable alternative: `start-{wf_id}`, where wf_id is the
        # Workflow ID.
        # How do we know if the user neglected to provide a name? self.name == self.id
        if '@name' not in event: #self._name == to_valid_k8s_name(self.id):
            self._name = to_valid_k8s_name(f'{START_EVENT_PREFIX}-{self.id}-{self._global_props.id}')

        self._kafka_topic = None

        self._service_properties.update({
            'host': self.name,
            'port': CATCH_LISTEN_PORT,
            'container': CATCH_IMAGE,
        })

        # Check if we listen to a kafka topic to start events.
        if self._annotation is not None and 'kafka_topic' in self._annotation:
            self._kafka_topic = self._annotation['kafka_topic']
            self._kafka_topics.append(self._kafka_topic)

        # if this is a timed start event, verify that the timer aspects are valid
        if self._timer_aspects:
            assert self._timer_aspects.recurrance >=0, f'Invalid recurrance for start event \'{self._timer_aspects.recurrance}\''

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
        assert self._namespace, "new-grad programmer error: namespace should be set by now."

        k8s_objects = []
        total_attempts = None
        target_url = None
        task_id = None

        outgoing_edges = list(edge_map[self.id])
        assert len(outgoing_edges) == 1, "Start Event must have excactly one outgoing edge."
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

        deployment_env_config = self.init_env_config() + \
        [
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
                "value": str(total_attempts),
            },
            {
                "name": "FORWARD_URL",
                "value": target_url,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": task_id,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": self.service_name,
            },
            {
                "name": "REXFLOW_FLOWD_HOST",
                "value": FLOWD_HOST,
            },
            {
                "name": "REXFLOW_FLOWD_PORT",
                "value": FLOWD_PORT,
            }
        ]
        if self._global_props.traffic_shadow_svc:
            deployment_env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_svc['k8s_url'],
            })

        if self._kafka_topic is not None:
            assert KAFKA_HOST is not None, "Kafka installation required for this BPMN Doc."
            deployment_env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._kafka_topic,
            })
            deployment_env_config.append({
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            })

        port = self.service_properties.port
        namespace = self._namespace
        k8s_objects.append(create_serviceaccount(namespace, self.service_name))
        k8s_objects.append(create_service(namespace, self.service_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            self.service_name,
            self.service_properties.container,
            port,
            deployment_env_config,
            etcd_access=True,
            kafka_access=True,
            priority_class=self.workflow_properties.priority_class,
        ))
        if CREATE_DEV_INGRESS:
            k8s_objects.append(create_rexflow_ingress_vs(
                namespace,
                self.service_name,
                uri_prefix=f'/{self.service_name}',
                dest_port=port,
                dest_host=f'{self.service_name}.{namespace}.svc.cluster.local',
            ))
        return k8s_objects
