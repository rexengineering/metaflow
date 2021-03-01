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
    create_deployment_affinity,
)

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

        self._service_name = self.name
        self._kafka_topic = None

        self._service_properties.update({
            'host': self._service_name,
            'port': THROW_LISTEN_PORT,
            'container': THROW_IMAGE,
        })

        # Check if we listen to a kafka topic to start events.
        if self._annotation is not None and 'kafka_topic' in self._annotation:
            self._kafka_topic = self._annotation['kafka_topic']

    def _to_kubernetes_reliable(self, id_hash, component_map: Mapping[str, BPMNComponent],
                                digraph: OrderedDict) -> list:
        '''Sets us up for reliable transport over Kafka.
        '''
        # Two things we need to do:
        # 1. Create the End Event (which uses the catch-gateway image)
        # 2. Per Hong's design, set up a python daemon that connects the End Event to the
        # previous step in the WF through its designated Kafka topic.
        assert KAFKA_HOST is not None, "Kafka Installation required for reliable WF."

        k8s_objects = []
        end_service_name = self.service_properties.host.replace('_', '-')
        namespace = self._namespace

        catch_service_name = f'{self.id}-{self.transport_kafka_topic}'.lower().replace("_", '-')

        # First, the Catch Event.
        deployment_env_config = [
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "REXFLOW_CATCH_START_FUNCTION",
                "value": "CATCH",
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
                "value": f"http://{end_service_name}.{self._namespace}:{THROW_LISTEN_PORT}/",
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": self.id,
            },
            {
                "name": "FAIL_URL",
                "value": "http://flowd.rexflow:9002/instancefail",
            },
            {
                "name": "KAFKA_GROUP_ID",
                "value": catch_service_name,
            },
            {
                "name": "ETCD_HOST",
                "value": os.environ['ETCD_HOST'],
            },
            {
                "name": "KAFKA_TOPIC",
                "value": self.transport_kafka_topic,
            }
        ]
        if self._global_props.traffic_shadow_svc:
            deployment_env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_svc['k8s_url'],
            })

        k8s_objects.append(create_serviceaccount(namespace, catch_service_name))
        k8s_objects.append(create_service(namespace, catch_service_name, CATCH_LISTEN_PORT))
        deployment = create_deployment(
            namespace,
            catch_service_name,
            CATCH_IMAGE,
            CATCH_LISTEN_PORT,
            deployment_env_config,
        )
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            end_service_name,
            catch_service_name,
        )
        k8s_objects.append(deployment)

        # Now create the daemon to connect End Event to First Task
        env_config = [
            {
                "name": "FORWARD_URL",
                "value": None,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": "",
            },
            {
                "name": "WF_ID",
                "value": self._global_props.id,
            },
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": '',
            },
            {
                "name": "REXFLOW_THROW_END_FUNCTION",
                "value": "END"
            },
            {
                "name": "ETCD_HOST",
                "value": ETCD_HOST,
            },
        ]
        if self._kafka_topic is not None:
            # We can still throw an Event at the end of the WF Instance
            env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._kafka_topic,
            })

        k8s_objects.append(create_serviceaccount(self._namespace, end_service_name))
        k8s_objects.append(create_service(self._namespace, end_service_name, THROW_LISTEN_PORT))
        k8s_objects.append(create_deployment(
            self._namespace,
            end_service_name,
            THROW_IMAGE,
            THROW_LISTEN_PORT,
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
        assert len(forward_set) == 0

        deployment_env_config = [
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
            {
                "name": "KAFKA_GROUP_ID",
                "value": dns_safe_name,
            }
        ]
        if self._kafka_topic is not None:
            assert KAFKA_HOST is not None, "Kafka installation required for this BPMN doc."
            deployment_env_config.append({
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            })
            deployment_env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._kafka_topic,
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
        return k8s_objects
