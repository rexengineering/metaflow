"""Utilities used in bpmn.py.
"""
from collections import OrderedDict
from typing import Any, Generator, Mapping, List, Set, Union, Optional
import yaml
from hashlib import sha1, sha256
import re
import json
from flowlib.constants import (
    BPMN_TIMER_EVENT_DEFINITION,
    TIMER_DESCRIPTION,
    TIMER_RECOVER_POLICY,
    to_valid_k8s_name,
    UserTaskPersistPolicy,
)
from flowlib.timer_util import TimedEventManager, ValidationResults, TimerRecoveryPolicy
from flowlib.config import (
    DEFAULT_NOTIFICATION_KAFKA_TOPIC,
    DEFAULT_USE_CLOSURE_TRANSPORT,
    WORKFLOW_PUBLISHER_LISTEN_PORT,
    DEFAULT_USE_SHARED_NAMESPACE
)


def get_edge_transport(edge, default_transport):
    transport = default_transport
    # Zeebe has no way to set any ancillary properties on the edge; therefore,
    # we rely upon the name annotation to mark an individual edge as kafka transport
    if edge.get('@name') == 'transport: kafka':
        transport = 'kafka'
    elif edge.get('@name') == 'transport: rpc':
        transport = 'rpc'
    return transport


def calculate_id_hash(wf_id: str) -> str:
    return sha1(wf_id.encode()).hexdigest()[:8]


def iter_xmldict_for_key(odict: OrderedDict, key: str) -> Generator[OrderedDict, None, None]:
    """Generator for iterating through an OrderedDict returned from xmltodict for a given key.
    """
    value = odict.get(key)
    if value:
        if isinstance(value, list):
            for child_value in value:
                yield child_value
        else:
            yield value


def raw_proc_to_digraph(proc: OrderedDict):
    """Takes in an OrderedDict (just the BPMN Process).
    Returns a directed graph, represented as a python dictionary, which shows the
    call dependencies of all of the BPMN components in the process.
    """
    digraph = dict()
    for sequence_flow in iter_xmldict_for_key(proc, 'bpmn:sequenceFlow'):
        source_ref = sequence_flow['@sourceRef']
        target_ref = sequence_flow['@targetRef']
        if source_ref not in digraph:
            digraph[source_ref] = set()
        digraph[source_ref].add(target_ref)
    return digraph


def outgoing_sequence_flow_table(proc: OrderedDict):
    """Takes in an OrderedDict (just the BPMN Process).
    Returns a dict mapping from a BPMN Component ID to a List of the outward
    edge id's flowing from that component.
    """
    outflows = {}
    for sequence_flow in iter_xmldict_for_key(proc, 'bpmn:sequenceFlow'):
        source_id = sequence_flow['@sourceRef']
        if source_id not in outflows:
            outflows[source_id] = []
        outflows[source_id].append(sequence_flow)
    return outflows


def get_annotations(process: OrderedDict, source_ref=None):
    """Takes in a BPMN process and BPMN Component ID and returns a generator.
    Yields python dictionaries containing the yaml-like REXFlow annotations
    from the BPMN Documents.
    """
    if source_ref is not None:
        targets = set()
        for association in iter_xmldict_for_key(process, 'bpmn:association'):
            if source_ref is None or association['@sourceRef'] == source_ref:
                targets.add(association['@targetRef'])
    else:
        targets = None
    for annotation in iter_xmldict_for_key(process, 'bpmn:textAnnotation'):
        if targets is None or annotation['@id'] in targets:
            text = annotation['bpmn:text']
            if text.startswith('rexflow:'):
                yield (annotation,yaml.safe_load(text.replace('\xa0', '')))


class ServiceProperties:
    def __init__(self, annotations: dict = None):
        self._host = None
        self._port = None
        self._protocol = None
        self._container_name = None
        self._id_hash = None
        self._is_hash_used = False
        self._namespace = None
        self._asynchronous = False
        if annotations:
            self.update(annotations)

    @property
    def namespace(self):
        assert self._namespace is not None, "Namespace should be set by now."
        return self._namespace

    @property
    def host_without_hash(self):
        """Returns the hostname for this K8s Service with the trailing id hash
        stripped (if the id hash exists).

        This is the host SHORT NAME and does NOT include the namespace.
        """
        return self._host

    @property
    def host(self):
        """Returns the host for the K8s Service corresponding to the owning
        BPMNComponent object. Note: if the Service is in a shared namespace,
        then the host returned will include the id hash at the end.

        This is the host SHORT NAME and does NOT include the namespace.
        """
        host = self._host
        if self._is_hash_used:
            assert self._id_hash, "The ID hash of the ServiceProperties should be set by now."
            host += f'-{self._id_hash}'
        return host

    @property
    def port(self):
        """Returns the port upon which this service listens.
        """
        return self._port if self._port is not None else 80

    @property
    def protocol(self):
        """Returns the protocol with which to communicate with this Service.
        """
        return self._protocol if self._protocol is not None else 'HTTP'

    @property
    def container(self):
        """Returns the docker image name for this k8s Service. Useful when creating
        Deployment objects.
        """
        return self._container_name

    @property
    def asynchronous(self):
        """Returns whether this is an Asynchronous Service.
        """
        return self._asynchronous

    def update(self, annotations):
        if 'host' in annotations:
            self._host = annotations['host'].replace('_', '-')
            if self._container_name is None:
                self._container_name = annotations['host']
        if 'port' in annotations:
            self._port = int(annotations['port'])
        if 'orchestrator' in annotations:
            self._orchestrator = annotations['orchestrator']
        if 'protocol' in annotations:
            self._protocol = annotations['protocol']
        if 'container' in annotations:
            self._container_name = annotations['container']
        if 'id_hash' in annotations:
            self._id_hash = annotations['id_hash']
        if 'hash_used' in annotations:
            self._is_hash_used = annotations['hash_used']
        if 'namespace' in annotations:
            self._namespace = annotations['namespace']
        if 'asynchronous' in annotations and annotations.get('asynchronous', False):
            self._asynchronous = True


class CallProperties:
    def __init__(self):
        self._path = None
        self._method = None
        self._serialization = None
        self._total_attempts = None

    @property
    def path(self) -> str:
        return self._path if self._path is not None else '/'

    @property
    def method(self) -> str:
        return self._method if self._method is not None else 'POST'

    @property
    def serialization(self) -> str:
        return self._serialization if self._serialization is not None else 'JSON'

    @property
    def total_attempts(self) -> int:
        """
        Returns total number of times to attempt calling this service, including retries.
        i.e. `total_attempts == 1` implies zero retries, `total_attempts == 3` implies two
        retries.
        """
        return self._total_attempts if self._total_attempts else 2

    def update(self, annotations: Mapping[str, Any]) -> None:
        if 'path' in annotations:
            self._path = annotations['path']
        if 'method' in annotations:
            self._method = annotations['method']
        if 'serialization' in annotations:
            self._serialization = annotations['serialization']
        if 'retry' in annotations:
            self._total_attempts = annotations['retry']['total_attempts']


class HealthProperties:
    def __init__(self):
        self._path = None
        self._method = None
        self.query = None
        self._period = None
        self._response = None
        self._timeout = None
        self._initial_delay = None
        self._failure_threshold = None

    @property
    def path(self) -> str:
        return self._path if self._path is not None else '/'

    @property
    def method(self) -> str:
        return self._method if self._method is not None else 'GET'

    @property
    def period(self) -> int:
        return self._period if self._period is not None else 30

    @property
    def response(self) -> str:
        return self._response if self._response is not None else 'HEALTHY'

    @property
    def timeout(self) -> int:
        return self._timeout if self._timeout else 5

    @property
    def initial_delay(self) -> int:
        return self._initial_delay if self._initial_delay else 30

    @property
    def failure_threshold(self) -> int:
        return self._failure_threshold if self._failure_threshold else 3

    def update(self, annotations):
        if 'path' in annotations:
            self._path = annotations['path']
        if 'method' in annotations:
            self._method = annotations['method']
        if 'query' in annotations:
            self.query = annotations['query']
        if 'period' in annotations:
            self._period = annotations['period']
        if 'response' in annotations:
            self._response = annotations['response']
        if 'timeout' in annotations:
            self._timeout = annotations['timeout']
        if 'initial_delay' in annotations:
            self._initial_delay = annotations['initial_delay']
        if 'failure_threshold' in annotations:
            self._failure_threshold = annotations['failure_threshold']


# TODO: Clean this up a bit
VALID_XGW_EXPRESSION_TYPES = [
    'python',
    'feel',
]


class WorkflowProperties:
    def __init__(self, annotations=None):
        self._orchestrator = 'istio'  # default to istio...
        self._id = ''
        self._namespace = None
        self._namespace_shared = DEFAULT_USE_SHARED_NAMESPACE
        self._id_hash = None
        self._retry_total_attempts = 1  # retry is opt-in feature: default no retry
        self._is_recoverable = False
        self._transport = 'rpc'
        self._notification_kafka_topic = DEFAULT_NOTIFICATION_KAFKA_TOPIC
        self._xgw_expression_type = 'feel'
        self._deployment_timeout = 180
        self._synchronous_wrapper_timeout = 10
        self._use_closure_transport = DEFAULT_USE_CLOSURE_TRANSPORT
        self._priority_class = None
        self._user_opaque_metadata = {}
        self._user_metadata = {}
        self._passthrough_target = None
        self._prefix_passthrough_with_namespace = False
        self._catch_event_expiration = 72
        self._timer_recovery_policy = TimerRecoveryPolicy.RECOVER_FAIL
        self._user_task_persist_policy = UserTaskPersistPolicy.PERSIST_NEVER
        if annotations is not None:
            if 'rexflow' in annotations:
                self.update(annotations['rexflow'])
            elif 'rexflow_global_properties' in annotations:
                self.update(annotations['rexflow_global_properties'])

    @property
    def id(self):
        return self._id

    @property
    def id_hash(self):
        assert self._id_hash is not None, "NewGradProgrammerError: id_hash should be set by now"
        return self._id_hash

    @property
    def namespace(self):
        return self._namespace if self._namespace is not None else 'default'

    @property
    def namespace_shared(self):
        return self._namespace_shared

    @property
    def retry_total_attempts(self):
        return self._retry_total_attempts

    @property
    def orchestrator(self):
        assert self._orchestrator == 'istio'
        return self._orchestrator if self._orchestrator is not None else 'docker'

    @property
    def is_recoverable(self):
        return self._is_recoverable

    @property
    def transport(self):
        return self._transport

    @property
    def traffic_shadow_call_props(self):
        if self._notification_kafka_topic is None:
            return None
        else:
            return CallProperties()

    @property
    def traffic_shadow_service_props(self):
        if self._notification_kafka_topic is None:
            return None
        else:
            return ServiceProperties({
                'host': f'wf-publisher-{self.id}',
                'namespace': self.namespace,
                'port': WORKFLOW_PUBLISHER_LISTEN_PORT,
            })

    @property
    def traffic_shadow_url(self):
        if not self.notification_kafka_topic:
            return None
        else:
            url = f'http://{self.traffic_shadow_service_props.host}.'
            url += self.traffic_shadow_service_props.namespace + "/"
            return url

    @property
    def notification_kafka_topic(self):
        return self._notification_kafka_topic

    @property
    def xgw_expression_type(self):
        return self._xgw_expression_type

    @property
    def deployment_timeout(self):
        return self._deployment_timeout

    @property
    def synchronous_wrapper_timeout(self):
        return self._synchronous_wrapper_timeout

    @property
    def use_closure_transport(self):
        return self._use_closure_transport

    @property
    def priority_class(self):
        return self._priority_class

    @property
    def user_opaque_metadata(self):
        """Retrieves opaque metadata set by user in this bpmn process.
        """
        return self._user_opaque_metadata

    @property
    def user_metadata(self):
        """Retrieves bpmn user_metadata
        """
        return self._user_metadata

    @property
    def passthrough_target(self):
        """As a development tool, we provide a Passthrough configuration option
        In this case, a user can deploy a workflow to his/her own docker-desktop
        cluster, and yet all service task calls will be "passed through" to a
        user-specified target url: `f'{host}.{passthrough_target}{passthrough_prefix}'`
        """
        return self._passthrough_target

    @property
    def prefix_passthrough_with_namespace(self):
        return self._prefix_passthrough_with_namespace

    @property
    def catch_event_expiration(self):
        return self._catch_event_expiration

    @property
    def timer_recovery_policy(self):
        return self._timer_recovery_policy

    @property
    def user_task_persist_policy(self):
        return self._user_task_persist_policy

    def update(self, annotations):
        if 'priority_class' in annotations:
            self._priority_class = annotations['priority_class']

        if 'use_closure_transport' in annotations:
            self._use_closure_transport = annotations['use_closure_transport']
            assert type(self._use_closure_transport) == bool

        if 'orchestrator' in annotations:
            assert annotations['orchestrator'] == 'istio'
            self._orchestrator = annotations['orchestrator']

        if 'namespace_shared' in annotations:
            self._namespace_shared = annotations['namespace_shared']

        if 'namespace' in annotations:
            assert self._namespace_shared, \
                "Can only specify namespace name if it's a pre-existing, shared NS."
            self._namespace = annotations['namespace']

        if 'id' in annotations:
            self._id = annotations['id']
            if not self._namespace_shared:
                self._namespace = self._id

        if 'recoverable' in annotations:
            self._is_recoverable = (annotations['recoverable'] or (self.transport == 'kafka'))

        if 'retry' in annotations:
            if 'total_attempts' in annotations['retry']:
                self._retry_total_attempts = annotations['retry']['total_attempts']

        if 'transport' in annotations:
            assert annotations['transport'] in ['kafka', 'rpc'], \
                "Only kafka and rpc transport are currently supported."
            self._transport = annotations['transport']
            if self._transport == 'kafka':
                self._is_recoverable = True

        if 'id_hash' in annotations:
            self._id_hash = annotations['id_hash']

        if 'deployment_timeout' in annotations:
            self._deployment_timeout = annotations['deployment_timeout']

        if 'synchronous_wrapper_timeout' in annotations:
            self._synchronous_wrapper_timeout = annotations['synchronous_wrapper_timeout']

        if 'notification_kafka_topic' in annotations:
            self._notification_kafka_topic = annotations['notification_kafka_topic']

        if 'xgw_expression_type' in annotations:
            assert annotations['xgw_expression_type'] in VALID_XGW_EXPRESSION_TYPES
            self._xgw_expression_type = annotations['xgw_expression_type']

        if 'user_opaque_metadata' in annotations:
            assert type(annotations['user_opaque_metadata']) == dict
            self._user_opaque_metadata.update(annotations['user_opaque_metadata'])

        if 'user_metadata' in annotations:
            assert type(annotations['user_metadata']) == dict
            self._user_metadata.update(annotations['user_metadata'])

        if 'passthrough_target' in annotations:
            self._passthrough_target = annotations['passthrough_target']
            if annotations.get('prefix_passthrough_with_namespace', False):
                self._prefix_passthrough_with_namespace = True

        if 'catch_event_expiration' in annotations:
            self._catch_event_expiration = annotations['catch_event_expiration']

        if 'timer_recovery_policy' in annotations:
            policy = annotations.get('timer_recovery_policy', 'fail')
            try:
                self._timer_recovery_policy = TimerRecoveryPolicy(policy)
            except ValueError:
                raise ValueError(f'Invalid timer_recovery_policy {policy}')

        if 'post_to_salesforce' in annotations:
            policy = annotations.get('post_to_salesforce', UserTaskPersistPolicy.PERSIST_NEVER)
            try:
                self._user_task_persist_policy = UserTaskPersistPolicy(policy)
            except ValueError:
                raise ValueError(f'Invalid post_to_salesforce value {policy}')

class BPMNComponent:
    """
    This is an abstract class for any BPMN Component. A Component may be a Task, Gateway,
    Throw Event, Catch Event, or more. In REXFlow, each Component is represented as
    a microservice. In all cases except for a Task, the microservice is automatically
    generated and configured using environment variables in the deployment.

    When we are creating the kubernetes yaml files, a Task, for example, needs to
    know where to forward its response to after completion (so that we may properly
    create the EnvoyFilter yaml). It is the responsibility of the BPMNTask object
    to have a way to find the correct next BPMNComponent object.

    The responsibility of the BPMNComponent object is to let the aforementioned
    BPMNTask object (it could've been a gateway, event, etc) know at which URL
    to reach the next component in the workflow.
    """
    def __init__(self,
                 spec: OrderedDict,
                 process: OrderedDict,
                 workflow_properties: WorkflowProperties,
                 default_is_preexisting: bool = False,
    ):
        self.id = spec['@id']

        annotations = [a for _,a in list(get_annotations(process, self.id)) if 'rexflow' in a]
        assert len(annotations) <= 1, "Can only provide one REXFlow annotation per BPMN Component."
        if len(annotations):
            self._annotation = annotations[0]['rexflow']
        else:
            self._annotation = None

        if '@name' in spec:
            self._name = to_valid_k8s_name(spec['@name'])
        else:
            self._name = to_valid_k8s_name(self.id)

        # Set default values. The constructors of child classes may override these values.
        # For example, a BPMNTask that calls a preexisting microservice should override
        # the value `self._is_preexisting`.
        self._is_preexisting = default_is_preexisting
        self._is_in_shared_ns = workflow_properties.namespace_shared
        self._namespace = workflow_properties.namespace
        self._health_properties = HealthProperties()
        self._service_properties = ServiceProperties()
        self._call_properties = CallProperties()
        self._global_props = workflow_properties
        self._proc = process
        self._kafka_topics = []
        self._timer_description = []
        self._timer_aspects: Optional[ValidationResults] = None
        self._timer_dynamic = False
        self._is_timer = False

        if self._annotation is not None and 'preexisting' in self._annotation:
            self._is_preexisting = self._annotation['preexisting']

        if BPMN_TIMER_EVENT_DEFINITION in spec:
            self._is_timer = True
            for key in ['timeDate', 'timeDuration', 'timeCycle']:
                tag = f'bpmn:{key}'
                if tag in spec[BPMN_TIMER_EVENT_DEFINITION]:
                    # run a validation against the spec so we can fail the apply rather than on run
                    # this will raise if there's anything seriously wrong. The finer points - like
                    # ranges and such - are verified by the individual component types.
                    self._timer_description = [key, spec[BPMN_TIMER_EVENT_DEFINITION][tag]['#text']]
                    self._timer_aspects, self._timer_dynamic = TimedEventManager.validate_spec(key, self._timer_description[1])
                    break
            assert self._timer_description, "timerEventDefinition has invalid timer type"
            self._timer_recovery_policy = workflow_properties._timer_recovery_policy

        service_update = {
            'hash_used': (self._global_props.namespace_shared and not self._is_preexisting),
            'id_hash': workflow_properties.id_hash
        }
        self._service_properties.update(service_update)

        # Set the default Retry Policy, which may or may not be overriden by each
        # individual BPMNComponent.
        self._call_properties.update(
            {'retry': {'total_attempts': self._global_props._retry_total_attempts}}
        )

        self.update_annotations()

    def update_annotations(self, annotation=None):
        if annotation is None:
            annotation = self._annotation
        elif self._annotation is None:
            self._annotation = annotation
        if annotation is not None:
            if 'call' in annotation:
                self._call_properties.update(annotation['call'])
            if 'health' in annotation:
                self._health_properties.update(annotation['health'])
            if 'service' in annotation:
                self._service_properties.update(annotation['service'])
            if 'timer_recovery_policy' in annotation:
                policy = annotation.get('timer_recovery_policy', 'fail')
                try:
                    self._timer_recovery_policy = TimerRecoveryPolicy(policy)
                except ValueError:
                    pass

    def init_env_config(self):
        if self._timer_description:
            return [
                {
                    'name': TIMER_DESCRIPTION,
                    'value': json.dumps(self._timer_description)
                },
                {
                    'name': TIMER_RECOVER_POLICY,
                    'value': self._timer_recovery_policy.name
                }
            ]
        return []

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: Mapping[str, Set[str]], sequence_flow_table: Mapping[str, Any]) -> list:
        """Takes in a dict which maps a BPMN component id* to a BPMNComponent Object,
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
        """
        raise NotImplementedError("Method must be overriden.")

    @property
    def name(self) -> str:
        """Returns the Name of this BPMN Object, conforming to the k8s name regex.
        This can be determined through any of two ways, in order of precedence:
        1. Directly putting a name on the BPMN object. For example, in a service task,
        this would be the text in the middle of the BPMN diagram. For an edge, it would
        be the visible text displayed just next to it. May return empty string.
        2. If the above is not specified, name() returns a k8s-safe version of the
        BPMN Component ID.
        """
        return self._name

    @property
    def namespace(self) -> str:
        """Returns the k8s namespace in which the corresponding k8s deployment for this
        BPMNComponent sits.
        """
        return self._namespace

    @property
    def deployment_timeout(self) -> int:
        """Returns time that healthd should wait when starting/stopping the deployment
        """
        return self.workflow_properties._deployment_timeout

    @property
    def is_in_shared_ns(self) -> bool:
        """Returns True if the k8s object corresponding to this BPMNComponent sits in
        a shared k8s namespace, as opposed to a namespace that is dedicated solely
        to this Workflow Deployment.
        """
        return self._is_in_shared_ns

    @property
    def is_preexisting(self) -> bool:
        """Returns True if the k8s object corresponding to this BPMNComponent was
        deployed separately from the Workflow; i.e. it was pre-existing.
        """
        return self._is_preexisting

    @property
    def health_properties(self) -> HealthProperties:
        """Returns the HealthProperties object for this BPMNComponent.
        """
        return self._health_properties

    @property
    def call_properties(self) -> CallProperties:
        """Returns the CallProperties object for this BPMNComponent.
        """
        return self._call_properties

    @property
    def service_properties(self) -> ServiceProperties:
        """Returns the ServiceProperties object for this BPMNComponent.
        """
        return self._service_properties

    @property
    def workflow_properties(self) -> WorkflowProperties:
        """Returns the WorkflowProperties object for this BPMNComponent.
        """
        return self._global_props

    @property
    def k8s_url(self) -> str:
        """Returns the fully-qualified host + path that is understood by the k8s
        kube-dns. For example, returns "http://my-service.my-namespace:my-port"
        """
        service_props = self.service_properties
        proto = service_props.protocol.lower()
        host = service_props.host
        port = service_props.port
        return f'{proto}://{host}.{self.namespace}:{port}{self.path}'

    @property
    def envoy_host(self) -> str:
        """Returns the Envoy-readable hostname for this service, for example
        "my-service.my-namespace.svc.cluster.local"
        """
        service_props = self.service_properties
        host = service_props.host
        return f'{host}.{self.namespace}.svc.cluster.local'

    @property
    def kafka_topics(self) -> List[str]:
        """List of kafka topics that need to get created for this BPMNComponent
        to run. Can include topics used for reliable transport and/or Events (eg. an
        intermediateThrowEvent.)
        """
        return self._kafka_topics

    @property
    def annotation(self) -> dict:
        """Returns the python dictionary representation of the rexflow annotation on the
        BPMN diagram for this BPMNComponent."""
        return self._annotation if self._annotation else dict()

    @property
    def path(self) -> str:
        """Returns the HTTP Path to call this component. The path refers to calling
        the BPMN component, and NOT the healthcheck.
        """
        call_props = self.call_properties
        path = call_props.path
        if not path.startswith('/'):
            path = '/' + path
        return path

    @property
    def service_name(self):
        """Returns the name of the k8s service. Same as the host.
        Just a convenience method.
        """
        return self.service_properties.host
