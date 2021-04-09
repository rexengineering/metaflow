'''
Implements the BPMNTask object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
from typing import List, Mapping

from .bpmn_util import (
    WorkflowProperties,
    BPMNComponent,
    get_edge_transport,
    iter_xmldict_for_key,
)

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)
from .config import CREATE_DEV_INGRESS
from .reliable_wf_utils import create_kafka_transport
from .constants import X_HEADER_TOKEN_POOL_ID

Upstream = namedtuple(
    'Upstream',
    ['full_hostname', 'port', 'path', 'method', 'total_attempts', 'task_id']
)

DEFAULT_TOKEN = '__DEFAULT__'

PARAM_TYPES = [
    'JSON_OBJECT',
    'STRING',
    'DOUBLE',
    'BOOLEAN',
    'INTEGER',
    'JSON_ARRAY',
]


def form_param_config(param):
    text = param['#text']
    param_type = text[:text.find("___")]
    name_text = param['@name']
    name = name_text[len(param_type) + len("___"):]

    assert name_text[:name_text.find("___")] == param_type
    assert param_type in PARAM_TYPES, f"Valid param types for Envoy: {PARAM_TYPES}"

    value = param['#text'][len(param_type) + len('___'):]
    default = None
    if value.startswith(DEFAULT_TOKEN):
        default = value[len(DEFAULT_TOKEN):]
        value = None
    elif '__DEFAULT__' in value:
        value, default = value.split('__DEFAULT__')

    return {
        'name': name,
        'value': value,
        'type': param_type,
        'default_value': default,
    }


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
        self._process = process

    def _generate_envoyfilter(self, upstreams: List[Upstream], component_map, edge_map) -> list:
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
            'closure_transport': self.workflow_properties.use_closure_transport,
            'headers_to_forward': [X_HEADER_TOKEN_POOL_ID.lower()],
            'upstream_port': self.service_properties.port,
            'inbound_retries': 0,
        }
        # Error Gateway stuff
        self.error_gateways = []
        for boundary_event in iter_xmldict_for_key(self._process, 'bpmn:boundaryEvent'):
            if 'bpmn:errorEventDefinition' not in boundary_event:
                continue
            if boundary_event['@attachedToRef'] == self.id:
                self.error_gateways.append(boundary_event)
        if len(self.error_gateways):
            assert len(self.error_gateways) == 1, \
                "Multiple error gateways for one task is unimplemented."
            boundary_event = self.error_gateways[0]
            outgoing_edge_list = edge_map[boundary_event['@id']]
            bavs_config['error_upstreams'] = []
            for edge in outgoing_edge_list:
                error_target = component_map[edge['@targetRef']]
                bavs_config['error_upstreams'].append(
                    self._make_forward(Upstream(
                        error_target.envoy_host,
                        error_target.service_properties.port,
                        error_target.call_properties.path,
                        error_target.call_properties.method,
                        error_target.call_properties.total_attempts,
                        error_target.id,
                    ))
                )

        # Smart Transport stuff
        if self.workflow_properties.use_closure_transport \
                    and 'bpmn:extensionElements' in self._task \
                    and 'camunda:inputOutput' in self._task['bpmn:extensionElements']:
            params = self._task['bpmn:extensionElements']['camunda:inputOutput']
            bavs_config['input_params'] = [
                form_param_config(param)
                for param in iter_xmldict_for_key(params, 'camunda:inputParameter')
            ]
            input_param_names = [param['name'] for param in bavs_config['input_params']]
            if '.' in input_param_names:
                assert len(input_param_names) == 1, "Can only have one top-level input param."
            bavs_config['output_params'] = [
                form_param_config(param)
                for param in iter_xmldict_for_key(params, 'camunda:outputParameter')
            ]
            output_param_values = [param['value'] for param in bavs_config['output_params']]
            if '.' in output_param_values:
                assert len(output_param_values) == 1, "Can only have one top-level output param."

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
                self.kafka_topics.append(transport_call_details.kafka_topic)
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

        k8s_objects.append(self._generate_envoyfilter(upstreams, component_map, edge_map))
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
            priority_class=self.workflow_properties.priority_class,
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
