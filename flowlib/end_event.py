'''
Implements BPMNEndEvent object, which does the bookkeeping associated with marking a WF Instance
as COMPLETED.
'''

from collections import OrderedDict
import os
from typing import Mapping

from .bpmn_util import BPMNComponent

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
)

from .reliable_wf_utils import create_reliable_wf_catcher

from .config import (
    ETCD_HOST,
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
)


END_EVENT_PREFIX = 'end'


class BPMNEndEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props):
        super().__init__(event, process, global_props)
        self._namespace = global_props.namespace

        self._kafka_topic = None

        self._service_properties.update({
            'host': self.name,
            'port': THROW_LISTEN_PORT,
            'container': THROW_IMAGE,
        })

        # Check if we listen to a kafka topic to start events.
        if self._annotation is not None and 'kafka_topic' in self._annotation:
            self._kafka_topic = self._annotation['kafka_topic']

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
        assert self._namespace, "new-grad programmer error: namespace should be set by now."

        k8s_objects = []
        port = self.service_properties.port
        namespace = self._namespace

        forward_set = list(digraph.get(self.id, set()))
        assert len(forward_set) == 0, "Can't have outgoing edge from End Event."

        deployment_env_config = self.init_env_config() + \
        [
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
                "name": "END_EVENT_NAME",
                "value": self.name,
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": self.service_name,
            }
        ]
        if self._kafka_topic is not None:
            assert KAFKA_HOST is not None, "Kafka installation required for this BPMN doc."
            deployment_env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._kafka_topic,
            })

        k8s_objects.append(create_serviceaccount(namespace, self.service_name))
        k8s_objects.append(create_service(namespace, self.service_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            self.service_name,
            self.service_properties.container,
            port,
            deployment_env_config,
            etcd_access=True,
            kafka_access=(self._kafka_topic is not None),
        ))
        return k8s_objects
