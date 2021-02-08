'''
Implements the BPMNTask object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
import os
from typing import List, Mapping

from .bpmn_util import WorkflowProperties, BPMNComponent

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
    create_deployment_affinity,
)


Upstream = namedtuple(
    'Upstream',
    ['name', 'host', 'port', 'path', 'method', 'total_attempts', 'task_id']
)
KAFKA_HOST = os.getenv("KAFKA_HOST", "my-cluster-kafka-bootstrap.kafka:9092")
ETCD_HOST = os.getenv("ETCD_HOST", "rexflow-etcd.rexflow:9002")
KAFKA_LISTEN_PORT = 5000


class BPMNTask(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(task, process, global_props)
        self._task = task

        assert 'service' in self._annotation, \
            "Must annotate Service Task with service information."

        assert 'host' in self._annotation['service'], \
            "Must annotate Service Task with service host."

        if self._is_preexisting:
            assert 'namespace' in self._annotation['service'], \
                "Must provide namespace of preexisting service."
            self._namespace = self._annotation['service']['namespace']

    def _generate_envoyfilter(self, upstreams: List[Upstream]) -> list:
        '''Generates a EnvoyFilter that appends the `bavs-filter` that we wrote to the Envoy
        FilterChain. This filter hijacks the response traffic and sends it to the next
        step of the workflow (whether that's a gateway, Event, or another ServiceTask.)
        '''
        # service_name is the name of the k8s service to which this EnvoyFilter is applied.
        # If it's a preexisting service, we look for the service's actual name (without the hash).
        if self._is_preexisting:
            service_name = self.service_properties.host_without_hash.replace('_', '-')
        else:
            service_name = self.service_properties.host.replace("_", '-')

        envoyfilter_name = self.service_properties.host.replace('_', '-')
        if self._is_preexisting:
            envoyfilter_name += f'-{self.id.lower().replace("_", "-")}'

        # We name the envoyfilter withhash if in a shared namespace and without hash
        # if it's not in a shared namespace, regardless of whether service is preexisting.
        # However, when the service is pre-existing, the service_properties.host does NOT
        # include the id_hash. Therefore, we must append the id_hash to envoyfilter name
        # IF the service is pre-existing.
        if self._is_preexisting:
            envoyfilter_name += '-' + self.workflow_properties.id_hash

        port = self.service_properties.port
        namespace = self._namespace  # namespace in which the k8s objects live.
        traffic_shadow_cluster = ''
        traffic_shadow_path = ''
        if self._global_props.traffic_shadow_svc:
            traffic_shadow_cluster = self._global_props.traffic_shadow_svc['envoy_cluster']
            traffic_shadow_path = self._global_props.traffic_shadow_svc['path']

        bavs_config = {
            'forwards': [
                self._make_forward(upstream) for upstream in upstreams
            ],
            'wf_id': self._global_props.id,
            'flowd_envoy_cluster': 'outbound|9002||flowd.rexflow.svc.cluster.local',
            'flowd_path': '/instancefail',
            'task_id': self.id,
            'traffic_shadow_cluster': traffic_shadow_cluster,
            'traffic_shadow_path': traffic_shadow_path,
        }
        envoy_filter = {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'EnvoyFilter',
            'metadata': {
                'name': envoyfilter_name,
                'namespace': namespace,
            },
            'spec': {
                'workloadSelector': {'labels': {'app': service_name}},
                'configPatches': [
                    {
                        'applyTo': 'HTTP_FILTER',
                        'match': {
                            'context': 'SIDECAR_INBOUND',
                            'listener': {
                                'portNumber': port,
                                'filterChain': {
                                    'filter': {
                                        'name': 'envoy.http_connection_manager',
                                        'subFilter': {'name': 'envoy.router'},
                                    },
                                },
                            },
                        },
                        'patch': {
                            'operation': 'INSERT_BEFORE',
                            'value': {
                                'name': 'bavs_filter',
                                'typed_config': {
                                    '@type': 'type.googleapis.com/udpa.type.v1.TypedStruct',
                                    'type_url': 'type.googleapis.com/bavs.BAVSFilter',
                                    'value': bavs_config,
                                },
                            },
                        },
                    },
                ]
            }
        }
        return envoy_filter

    def _to_kubernetes_reliable(self, id_hash, component_map: Mapping[str, BPMNComponent],
                                digraph: OrderedDict) -> list:
        '''Generates kubernetes deployment for reliable workflow using Kafka transport.
        '''
        k8s_objects = []
        if self._is_preexisting:
            service_name = self.service_properties.host_without_hash.replace('_', '-')
        else:
            service_name = self.service_properties.host.replace("_", '-')

        # There are three things to do:
        # 1. Generate the first Python service which listens for incoming calls on the Kafka topic
        # and calls the service
        # 2. Generate the second Python service, which listens for the response and throws it to
        # the next kafka topic
        # 3. Put an envoyfilter on the service (and optionally create the service itself if not
        # preexisting)

        # Step 1: Make the first python service. Uses the catch_gateway.
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
                # Despite this being a separate K8s service, the envoyfilter on the service we
                # forward to expects the same task id as the id of this BPMNTask Object.
                "value": self.id,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": 1,  # For reliable workflows, only try once.
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
        k8s_objects.append(create_serviceaccount(self._namespace, self.transport_kafka_topic))
        k8s_objects.append(
            create_service(self._namespace, self.transport_kafka_topic, KAFKA_LISTEN_PORT)
        )
        deployment = create_deployment(
            self._namespace,
            self.transport_kafka_topic,
            'catch-gateway:1.0.0',
            KAFKA_LISTEN_PORT,
            env_config,
        )
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            service_name,
            self.transport_kafka_topic,
        )
        k8s_objects.append(deployment)

        # Step 2: Make the Kafka thing that receives the response and throws it at the next object.
        forward_set = list(digraph.get(self.id, set()))
        assert len(forward_set) == 1
        forward_id = forward_set[0]
        forward_component = component_map[forward_id]

        env_config = [
            {
                "name": "KAFKA_TOPIC",
                "value": forward_component.transport_kafka_topic,
            },
            {
                "name": "FORWARD_URL",
                "value": None,
            },
            {
                "name": "TOTAL_ATTEMPTS",
                "value": None,
            },
            {
                "name": 'KAFKA_HOST',
                "value": KAFKA_HOST,
            },
            {
                "name": "FORWARD_TASK_ID",
                "value": forward_component.id,
            },
        ]

        throw_service_name = f'{self.id}-{forward_component.transport_kafka_topic}'.lower()
        throw_service_name = throw_service_name.replace('_', '-')

        k8s_objects.append(
            create_serviceaccount(self._namespace, throw_service_name)
        )
        k8s_objects.append(
            create_service(
                self._namespace,
                throw_service_name,
                KAFKA_LISTEN_PORT,
            )
        )
        deployment = create_deployment(
            self._namespace,
            throw_service_name,
            'throw-gateway:1.0.0',
            KAFKA_LISTEN_PORT,
            env_config,
        )
        deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
            service_name,
            throw_service_name,
        )
        k8s_objects.append(deployment)

        # Finally, create the envoyfilter.
        k8s_objects.append(
            self._generate_envoyfilter(
                [
                    Upstream(
                        forward_component.transport_kafka_topic,
                        f'{throw_service_name}.{self._namespace}.svc.cluster.local',
                        KAFKA_LISTEN_PORT,
                        '/',
                        'POST',
                        1,
                        self.id,
                    )
                ]
            )
        )

        if not self._is_preexisting:
            k8s_objects.extend(self._generate_microservice())
        return k8s_objects

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict) -> list:
        '''Takes in a dict which maps a BPMN component id* to a BPMNComponent Object,
        and an OrderedDict which represents the whole BPMN Process as a directed graph.
        The digraph maps from {TaskId -> set(TaskId)}.
        Returns a list of kubernetes objects in python dict (i.e. json) format. Each
        BPMN component is implemented in REXFlow as a k8s Service. Therefore, each
        BPMNComponent Object's to_kubernetes() function should yield:
        - A k8s Service
        - A k8s Deployment
        - A k8s networking.istio.io/v1alpha1.EnvoyFilter (optional)
        - A k8s ServiceAccount (optional)
        - A k8s VirtualService (optional, used ONLY for debugging **)

        Notes:
        * BPMN Component Id's come from the BPMN XML document.

        ** For now, the BAVS Filter does not support routing according to
           VS rules. The use-case for a VS would be for docker-desktop dev,
           so that the developer may send traffic from his/her terminal into
           the cluster (i.e. the VS attaches to a Gateway).
        '''
        if self._global_props._is_reliable_transport:
            return self._to_kubernetes_reliable(id_hash, component_map, digraph)

        k8s_objects = []
        forward_bpmn_objects = [] # type: List[BPMNComponent]
        forward_set = digraph.get(self.id, set())
        for forward in forward_set:
            bpmn_component = component_map[forward] # type: BPMNComponent
            forward_bpmn_objects.append(bpmn_component)

        upstreams = [] # type: list[Upstream]
        for bpmn_component in forward_bpmn_objects:
            path = bpmn_component.call_properties.path
            if not path.startswith('/'):
                path = '/' + path
            upstreams.append(
                Upstream(
                    bpmn_component.service_properties.host,
                    bpmn_component.envoy_host,
                    bpmn_component.service_properties.port,
                    path,
                    bpmn_component.call_properties.method,
                    bpmn_component.call_properties.total_attempts,
                    bpmn_component.id,
                )
            )

        k8s_objects.append(self._generate_envoyfilter(upstreams))
        if not self._is_preexisting:
            k8s_objects.extend(self._generate_microservice())
        return k8s_objects

    def _generate_microservice(self):
        k8s_objects = []
        # Reminder: ServiceProperties.host() properly handles whether or not to include
        # id hash.
        service_name = self.service_properties.host
        dns_safe_name = service_name.replace('_', '-')

        # k8s ServiceAccount
        port = self.service_properties.port
        namespace = self._namespace
        assert self.namespace, "new-grad programmer error: namespace should be set by now."
        uri_prefix = f'/{service_name}' if namespace == 'default' \
            else f'/{namespace}/{service_name}'

        k8s_objects.append(create_serviceaccount(namespace, dns_safe_name))
        k8s_objects.append(create_service(namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            dns_safe_name,
            self.service_properties.container,
            port,
            env=[],
        ))
        k8s_objects.append(create_rexflow_ingress_vs(
            namespace,
            f'{dns_safe_name}-{self._global_props.id_hash}',
            uri_prefix=uri_prefix,
            dest_port=port,
            dest_host=f'{dns_safe_name}.{namespace}.svc.cluster.local',
        ))

        return k8s_objects

    def _make_forward(self, upstream: Upstream):
        return {
            'name': upstream.name,
            'cluster': upstream.name,
            'host': upstream.host,
            'port': upstream.port,
            'path': upstream.path,
            'method': upstream.method, # TODO: Test with methods other than POST
            'total_attempts': upstream.total_attempts,
            'task_id': upstream.task_id,
        }
