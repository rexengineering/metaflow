'''
Implements the BPMNTask object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
from typing import List, Mapping

from .bpmn_util import WorkflowProperties, BPMNComponent, get_edge_transport

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)
from .config import CREATE_DEV_INGRESS
from .reliable_wf_utils import create_kafka_transport

Upstream = namedtuple(
    'Upstream',
    ['full_hostname', 'port', 'path', 'method', 'total_attempts', 'task_id']
)


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
            if 'health' not in self._annotation:
                # Can't make guarantee about where the service implementor put
                # their health endpoint, so (for now) require it to be specified.
                self._health_properties = None

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

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
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
        k8s_objects = []

        outgoing_edges = list(edge_map[self.id])
        assert len(outgoing_edges) > 0, "Cannot have dead end on service task."

        upstreams = [] # list of Upstreams. This gets passed into the Envoyfilter config.

        for edge in outgoing_edges:
            assert edge['@sourceRef'] == self.id, "NewGradProgrammerError: invalid edge map."
            transport = get_edge_transport(edge, self._global_props.transport)
            target = component_map[edge['@targetRef']] # type: BPMNComponent

            if transport == 'kafka':
                transport_call_details = create_kafka_transport(self, target)
                k8s_objects.extend(transport_call_details.k8s_specs)
                upstreams.append(
                    Upstream(
                        transport_call_details.envoy_host,
                        transport_call_details.port,
                        transport_call_details.path,
                        transport_call_details.method,
                        transport_call_details.total_attempts,
                        self.id,
                    )
                )
            else:
                path = target.call_properties.path
                if not path.startswith('/'):
                    path = '/' + path
                upstreams.append(
                    Upstream(
                        target.envoy_host,
                        target.service_properties.port,
                        path,
                        target.call_properties.method,
                        target.call_properties.total_attempts,
                        target.id,
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

        # k8s ServiceAccount
        port = self.service_properties.port
        namespace = self._namespace
        assert self.namespace, "new-grad programmer error: namespace should be set by now."
        uri_prefix = f'/{service_name}' if namespace == 'default' \
            else f'/{namespace}/{service_name}'

        k8s_objects.append(create_serviceaccount(namespace, self.service_name))
        k8s_objects.append(create_service(namespace, self.service_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            self.service_name,
            self.service_properties.container,
            port,
            env=[],
        ))
        if CREATE_DEV_INGRESS:
            k8s_objects.append(create_rexflow_ingress_vs(
                namespace,
                f'{self.service_name}-{self._global_props.id_hash}',
                uri_prefix=uri_prefix,
                dest_port=port,
                dest_host=f'{self.service_name}.{namespace}.svc.cluster.local',
            ))

        return k8s_objects

    def _make_forward(self, upstream: Upstream):
        return {
            'full_hostname': upstream.full_hostname,
            'port': upstream.port,
            'path': upstream.path,
            'method': upstream.method, # TODO: Test with methods other than POST
            'total_attempts': upstream.total_attempts,
            'task_id': upstream.task_id,
        }
