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
    create_rexflow_ingress_vs,
    create_deployment_affinity,
)

END_EVENT_PREFIX = 'end'
END_EVENT_LISTEN_PORT = '5000'
END_EVENT_CONTAINER = 'throw-gateway:1.0.0'
KAFKA_LISTEN_PORT = '5000'
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")


class BPMNEndEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, event: OrderedDict, process: OrderedDict, global_props):
        super().__init__(event, process, global_props)
        self._namespace = global_props.namespace

        assert 'service' in self._annotation, \
            "Must provide service host annotation for all End Events."

        assert 'host' in self._annotation['service'], \
            "Must provide service host annotation for all End Events."

        assert 'port' not in self._annotation['service'], \
            "End Event Service Port is auto-configured."

        self._service_name = f"{END_EVENT_PREFIX}-{self._annotation['service']['host']}"
        self._queue = None

        self._service_properties.update({
            'host': self._service_name,
            'port': END_EVENT_LISTEN_PORT,
            'container': END_EVENT_CONTAINER,
        })

        # Check if we listen to a kafka topic to start events.
        if 'queue' in self._annotation:
            self._queue = self._annotation['queue']

    def _to_kubernetes_reliable(self, id_hash, component_map: Mapping[str, BPMNComponent],
                                digraph: OrderedDict) -> list:
        '''Sets us up for reliable transport over Kafka.
        '''
        # Two things we need to do:
        # 1. Create the End Event (which uses the catch-gateway image)
        # 2. Per Hong's design, set up a python daemon that connects the End Event to the
        # previous step in the WF through its designated Kafka topic.

        k8s_objects = []
        end_service_name = self.service_properties.host.replace('_', '-')
        port = self.service_properties.port
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
                "value": f"http://{end_service_name}.{self._namespace}:{KAFKA_LISTEN_PORT}/",
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
        k8s_objects.append(create_service(namespace, catch_service_name, port))
        deployment = create_deployment(
            namespace,
            catch_service_name,
            "catch-gateway:1.0.0",
            port,
            deployment_env_config,
        )
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            end_service_name,
            catch_service_name,
        )
        k8s_objects.append(deployment)

        k8s_objects.append(create_rexflow_ingress_vs(
            namespace,
            catch_service_name,
            uri_prefix=f'/{catch_service_name}',
            dest_port=port,
            dest_host=f'{catch_service_name}.{namespace}.svc.cluster.local',
        ))

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
                "value": os.getenv('ETCD_HOST', 'rexflow-etcd.rexflow:9002'),
            },
        ]
        if self._queue is not None:
            # We can still throw an Event at the end of the WF Instance
            env_config.append({
                "name": "KAFKA_TOPIC",
                "value": self._queue,
            })

        k8s_objects.append(create_serviceaccount(self._namespace, end_service_name))
        k8s_objects.append(create_service(self._namespace, end_service_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            end_service_name,
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
        assert len(forward_set) == 0

        deployment_env_config = [
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
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
