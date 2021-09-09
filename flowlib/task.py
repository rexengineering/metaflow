'''
Implements the BPMNTask object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
import json
from typing import List, Mapping, Any
import yaml

from .bpmn_util import (
    BPMN,
    WorkflowProperties,
    ServiceProperties,
    CallProperties,
    HealthProperties,
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
from .config import (
    CREATE_DEV_INGRESS,
    DEFAULT_USE_PREEXISTING_SERVICES,
    FLOWD_HOST,
    FLOWD_PORT,
    INSTANCE_FAIL_ENDPOINT_PATH,
    ASYNC_BRIDGE_IMAGE,
    ASYNC_BRIDGE_LISTEN_PORT,

)
from .reliable_wf_utils import create_kafka_transport
from .constants import Headers, to_valid_k8s_name

Upstream = namedtuple(
    'Upstream',
    ['full_hostname', 'port', 'path', 'method', 'total_attempts', 'task_id']
)

DEFAULT_TOKEN = '___DEFAULT___'

PARAM_TYPES = [
    'JSON_OBJECT',
    'STRING',
    'DOUBLE',
    'BOOLEAN',
    'INTEGER',
    'JSON_ARRAY',
]
DEFAULT_PARAM_TYPE = 'JSON_OBJECT'


def form_param_config(param):
    '''Takes in a `camunda:inputOutputParameter`. If curious, look in the bpmn xml.
    '''
    name = param['@name']
    text = param['#text'].replace('\xa0', '')
    lines = text.split('\n')
    assert len(lines) > 0, "Must annotate variables with assignment value."

    split_first_line = lines[0].split(': ')
    if len(split_first_line):
        value, param_type = split_first_line[0], split_first_line[1]
    else:
        value, param_type = split_first_line[0], DEFAULT_PARAM_TYPE

    if len(lines) > 1:
        default_value_line = lines[1]
        assert default_value_line.startswith('default: '), \
            "second line of param config should specify default value. Syntax: `default: <value>`"
        default_value = default_value_line[len('default: '):]
        has_default_value = True
    else:
        has_default_value = False
        default_value = None

    result = {
        'name': name,
        'value': value,
        'type': param_type,
        'has_default_value': has_default_value,
        'default_value': default_value,
    }
    return result


class BPMNTask(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self,
        task: OrderedDict,
        process: OrderedDict,
        global_props: WorkflowProperties,
        default_is_preexisting: bool = DEFAULT_USE_PREEXISTING_SERVICES,
    ):
        super().__init__(task, process, global_props, default_is_preexisting=default_is_preexisting)
        self._task = task

        # Metadata should be processed in reverse priority, and independent of
        # other metadata sources.
        if BPMN.documentation in task and task[BPMN.documentation].startswith('rexflow:'):
            # Third priority: check for annotations in the documentation.
            self.update_annotations(yaml.safe_load(task[BPMN.documentation])['rexflow'])
        if BPMN.extension_elements in task:
            # Second priority: check for Camunda extensions.
            extensions = task[BPMN.extension_elements]
            if (('camunda:connector' in extensions)
                and ('camunda:connectorId' in extensions['camunda:connector'])):

                hostname = extensions['camunda:connector']['camunda:connectorId']
                self._service_properties.update({
                    'host': hostname,
                    'container': hostname,
                })
        # TODO: This ad hoc property usage is a nasty hack, and should have
        # never been introduced into the code base.  Rename `targetPort` to
        # `target_port` and make it a proper service property.
        if ((self._annotation is not None)
            and ('service' in self._annotation)
            and ('targetPort' in self._annotation['service'])):
            # First priority: check for properties set in an annotation.
            self._target_port = self._annotation['service']['targetPort']
        else:
            self._target_port = self.service_properties.port

        # The `.service_properties` and `.call_properties` properties of BPMNComponent
        # classes are used by _other_ BPMNComponents to know how to communicate with this
        # BPMNComponent. Therefore, we want the `_service_properties` and `_call_properties`
        # properties of this BPMNComponent to refer to where we want people to send traffic
        # to. If this is a synchronous task, we're fine; just leave them as-is. But if
        # we are an asynchronous task, we want other components to communicate with
        # the Async Service Bridge and NOT the actual service.
        # Because we (the BPMNTask implementor) care about the location of the worker
        # service, we save that info before fudging it.
        self._worker_service_name = self.service_name
        self._worker_call_properties = self._call_properties
        self._worker_service_properties = self._service_properties
        if self._service_properties.asynchronous:
            self._service_properties = ServiceProperties()
            self._service_properties.update({
                'namespace': self.namespace,
                'port': ASYNC_BRIDGE_LISTEN_PORT,
                'container': self._service_properties.container,
                'host': to_valid_k8s_name(f'bridge-{self._worker_service_name}-{self.id}'),
                'hash_used': self.workflow_properties.namespace_shared,
                'id_hash': self.workflow_properties.id_hash,
            })
            self._call_properties = CallProperties()
            self._call_properties.update({
                'path': '/',
                'method': 'POST',
            })

        if self._is_preexisting and self._annotation is not None:
            self._namespace = self._annotation['service'].get('namespace', global_props.namespace)
            if 'health' not in self._annotation:
                # Can't make guarantee about where the service implementor put
                # their health endpoint, so (for now) require it to be specified.
                self._health_properties = None
        self._process = process
        self.is_passthrough = (
            self._is_preexisting and (self._global_props.passthrough_target is not None)
        )

    def _generate_envoyfilter(self, upstreams: List[Upstream], component_map, edge_map) -> dict:
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

        namespace = self._namespace  # namespace in which the k8s objects live.
        if self._global_props.notification_kafka_topic:
            shadow_svc = self._global_props.traffic_shadow_service_props
            shadow_call = self._global_props.traffic_shadow_call_props
            host = f'{shadow_svc.host}.{shadow_svc.namespace}.svc.cluster.local'
            shadow_upstream = Upstream(
                host,
                shadow_svc.port,
                shadow_call.path,
                shadow_call.method,
                0,
                ''
            )
        else:
            shadow_upstream = Upstream('', 0, '', '', 0, '')

        # Error Gateway stuff
        error_gateways = []
        for boundary_event in iter_xmldict_for_key(self._process, BPMN.boundary_event):
            if BPMN.error_event_definition not in boundary_event:
                continue
            if boundary_event['@attachedToRef'] == self.id:
                error_gateways.append(boundary_event)
        error_upstream_configs = []
        if len(error_gateways):
            assert len(error_gateways) == 1, \
                "Multiple error gateways for one task is unimplemented."
            boundary_event = error_gateways[0]
            outgoing_edge_list = edge_map[boundary_event['@id']]
            for edge in outgoing_edge_list:
                error_target = component_map[edge['@targetRef']]
                error_upstream_configs.append(
                    self._make_upstreamconfig(Upstream(
                        error_target.envoy_host,
                        error_target.service_properties.port,
                        error_target.call_properties.path,
                        error_target.call_properties.method,
                        error_target.call_properties.total_attempts,
                        error_target.id,
                    ))
                )

        input_params, output_params = self._generate_bavs_params()

        flowd_host = FLOWD_HOST
        if not flowd_host.endswith('.svc.cluster.local'):
            flowd_host += '.svc.cluster.local'
        bavs_config = {
            'inbound_upstream': self._make_upstreamconfig(Upstream(
                self.envoy_host,
                self._target_port,
                self._worker_call_properties.path,
                self._worker_call_properties.method,
                self._worker_call_properties.total_attempts,
                self.id,
            )),
            'forward_upstreams': [
                self._make_upstreamconfig(upstream) for upstream in upstreams
            ],
            'flowd_upstream': self._make_upstreamconfig(Upstream(
                flowd_host,
                FLOWD_PORT,
                INSTANCE_FAIL_ENDPOINT_PATH,
                'POST',
                1,
                '',
            )),
            'shadow_upstream': self._make_upstreamconfig(shadow_upstream),
            'error_gateway_upstreams': error_upstream_configs,
            'headers_to_forward': [Headers.X_HEADER_TOKEN_POOL_ID.lower()],
            'closure_transport': self.workflow_properties.use_closure_transport,
            'wf_did': self._global_props.id,
            'input_params': input_params,
            'output_params': output_params,
            'wf_did_header': Headers.X_HEADER_WORKFLOW_ID.lower(),
            'wf_tid_header': Headers.X_HEADER_TASK_ID.lower(),
            'wf_iid_header': Headers.X_HEADER_FLOW_ID.lower(),
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
                                'portNumber': self._target_port,
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

        # List of Upstreams representing outbound edges
        upstreams = [] # type: List[Upstream]

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

        if not self._worker_service_properties.asynchronous:
            k8s_objects.append(self._generate_envoyfilter(upstreams, component_map, edge_map))
        else:
            # We need to create the AsyncServiceBridge.
            k8s_objects.extend(
                self._generate_async_bridge(upstreams, component_map, edge_map)
            )
        if not self._is_preexisting:
            k8s_objects.extend(self._generate_microservice())
        return k8s_objects

    def _generate_async_bridge(
        self,
        upstreams: List[Upstream],
        component_map: Mapping[str, BPMNComponent],
        edge_map: Mapping[str, Any],
    ) -> List[dict]:
        '''Generates K8s manifest for the Async Service Bridge
        '''
        assert self._worker_service_properties.asynchronous

        result = []

        # generate forward tasks
        forward_tasks = []
        for upstream in upstreams:
            forward_tasks.append({
                'method': upstream.method,
                'k8s_url': f'http://{upstream.full_hostname}:{upstream.port}{upstream.path}',
                'task_id': upstream.task_id,
                'total_attempts': upstream.total_attempts,
            })
        worker_url = f"http://{self._worker_service_properties.host}.{self.namespace}"
        worker_url += f":{self._worker_service_properties.port}"
        worker_url += self._worker_call_properties.path

        bavs_params = {}
        if self.workflow_properties.use_closure_transport:
            bavs_params['input_params'], bavs_params['output_params'] = self._generate_bavs_params()

        env_config = [
            {
                "name": "ASYNC_TASK_URL",
                "value": worker_url
            },
            {
                "name": "ASYNC_BRIDGE_HOST",
                "value": self.k8s_url,
            },
            {
                "name": "ASYNC_TASK_ID",
                "value": self.id,
            },
            {
                "name": "CLOSURE_TRANSPORT",
                "value": "true" if self.workflow_properties.use_closure_transport else "false",
            },
            {
                "name": "ASYNC_BRIDGE_FORWARD_TASKS",
                "value": json.dumps(forward_tasks),
            },
            {
                "name": "ASYNC_BRIDGE_CONTEXT_PARAMETERS",
                "value": json.dumps(bavs_params),
            },
            {
                "name": "WF_ID",
                "value": self.workflow_properties.id,
            }
        ]
        result.append(create_service(
            self.namespace,
            self.service_name,
            self.service_properties.port,
        ))
        result.append(create_deployment(
            self.namespace,
            self.service_name,
            ASYNC_BRIDGE_IMAGE,
            ASYNC_BRIDGE_LISTEN_PORT,
            env_config,
            etcd_access=True,
            kafka_access=True,
            priority_class=self.workflow_properties.priority_class,
            health_props=HealthProperties(),
        ))
        result.append(create_serviceaccount(
            self.namespace,
            self.service_name,
        ))

        return result

    def _generate_microservice(self):
        k8s_objects = []
        # Reminder: ServiceProperties.host() properly handles whether or not to include
        # id hash.
        service_name = self.service_properties.host

        # k8s ServiceAccount
        port = self.service_properties.port
        target_port = self._target_port
        namespace = self._namespace
        assert self.namespace, "new-grad programmer error: namespace should be set by now."
        uri_prefix = f'/{service_name}' if namespace == 'default' \
            else f'/{namespace}/{service_name}'

        k8s_objects.append(create_serviceaccount(namespace, self._worker_service_name))
        k8s_objects.append(
            create_service(namespace, self._worker_service_name, port, target_port=target_port)
        )
        k8s_objects.append(create_deployment(
            namespace,
            self._worker_service_name,
            self._worker_service_properties.container,
            target_port,
            env=[],
            priority_class=self.workflow_properties.priority_class,
            health_props=self.health_properties,
        ))
        if CREATE_DEV_INGRESS:
            k8s_objects.append(create_rexflow_ingress_vs(
                namespace,
                f'{self._worker_service_name}-{self._global_props.id_hash}',
                uri_prefix=uri_prefix,
                dest_port=port,
                dest_host=f'{self._worker_service_name}.{namespace}.svc.cluster.local',
            ))

        return k8s_objects

    def _generate_bavs_params(self):
        # Smart Transport stuff
        if self.workflow_properties.use_closure_transport \
                    and BPMN.extension_elements in self._task \
                    and 'camunda:inputOutput' in self._task[BPMN.extension_elements]:
            params = self._task[BPMN.extension_elements]['camunda:inputOutput']
            input_params = [
                form_param_config(param)
                for param in iter_xmldict_for_key(params, 'camunda:inputParameter')
            ]
            input_param_names = [param['name'] for param in input_params]
            if '.' in input_param_names:
                assert len(input_param_names) == 1, "Can only have one top-level input param."
            output_params = [
                form_param_config(param)
                for param in iter_xmldict_for_key(params, 'camunda:outputParameter')
            ]
            output_param_values = [param['value'] for param in output_params]
            if '.' in output_param_values:
                assert len(output_param_values) == 1, "Can only have one top-level output param."
        else:
            input_params = []
            output_params = []
        return input_params, output_params

    def _make_upstreamconfig(self, upstream: Upstream):
        return {
            'full_hostname': upstream.full_hostname,
            'port': upstream.port,
            'path': upstream.path,
            'method': upstream.method, # TODO: Test with methods other than POST
            'total_attempts': upstream.total_attempts,
            'wf_tid': upstream.task_id,
        }
