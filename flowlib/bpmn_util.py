'''Utilities used in bpmn.py.
'''
from collections import OrderedDict
from typing import Any, Mapping, List
import yaml
from hashlib import sha1


def calculate_id_hash(wf_id: str) -> str:
    return sha1(wf_id.encode()).hexdigest()[:8]


def iter_xmldict_for_key(odict: OrderedDict, key: str):
    '''Generator for iterating through an OrderedDict returned from xmltodict for a given key.
    '''
    value = odict.get(key)
    if value:
        if isinstance(value, list):
            for child_value in value:
                yield child_value
        else:
            yield value


def raw_proc_to_digraph(proc: OrderedDict):
    '''Takes in an OrderedDict (just the BPMN Process).
    Returns a directed graph, represented as a python dictionary, which shows the
    call dependencies of all of the BPMN components in the process.
    '''
    digraph = dict()
    for sequence_flow in iter_xmldict_for_key(proc, 'bpmn:sequenceFlow'):
        source_ref = sequence_flow['@sourceRef']
        target_ref = sequence_flow['@targetRef']
        if source_ref not in digraph:
            digraph[source_ref] = set()
        digraph[source_ref].add(target_ref)
    return digraph


def outgoing_sequence_flow_table(proc: OrderedDict):
    '''Takes in an OrderedDict (just the BPMN Process).
    Returns a dict mapping from a BPMN Component ID to a List of the outward
    edge id's flowing from that component.
    '''
    outflows = {}
    for sequence_flow in iter_xmldict_for_key(proc, 'bpmn:sequenceFlow'):
        source_id = sequence_flow['@sourceRef']
        if source_id not in outflows:
            outflows[source_id] = []
        outflows[source_id].append(sequence_flow)
    return outflows


def get_annotations(process: OrderedDict, source_ref=None):
    '''Takes in a BPMN process and BPMN Component ID and returns a generator.
    Yields python dictionaries containing the yaml-like REXFlow annotations
    from the BPMN Documents.
    '''
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
                yield yaml.safe_load(text.replace('\xa0', ''))


def parse_events(process: OrderedDict):
    '''Accepts OrderedDict representing BPMN XML document. Returns a dict of form:
    {
        'catch': [list of Catch Events],
        'throw': [list of Throw Events],
    }
    '''
    # For now, to avoid forcing the user of REXFlow to have to annotate each event
    # as either a Throw or Catch, we will infer based on the following rule:
    # If there is an incoming edge to the Event in self.to_digraph, then
    # it's a Throw event. Else, it's a Catch event.
    all_events = [event for event in iter_xmldict_for_key(process, 'bpmn:intermediateThrowEvent')]
    out = {'throw': [], 'catch': []}
    for event in all_events:
        if 'bpmn:incoming' in event:
            out['throw'].append(event)
        else:
            out['catch'].append(event)
    return out


class ServiceProperties:
    def __init__(self, annotations: dict = None):
        self._host = None
        self._port = None
        self._protocol = None
        self._container_name = None
        self._id_hash = None
        self._is_hash_used = False
        self._namespace = None
        if annotations:
            self.update(annotations)

    @property
    def namespace(self):
        assert self._namespace is not None, "Namespace should be set by now."
        return self._namespace

    @property
    def host_without_hash(self):
        '''Returns the hostname for this K8s Service with the trailing id hash
        stripped (if the id hash exists).
        '''
        return self._host

    @property
    def host(self):
        '''Returns the host for the K8s Service corresponding to the owning
        BPMNComponent object. Note: if the Service is in a shared namespace,
        then the host returned will include the id hash at the end.
        '''
        host = self._host
        if self._is_hash_used:
            assert self._id_hash, "The ID hash of the ServiceProperties should be set by now."
            host += f'-{self._id_hash}'
        return host

    @property
    def port(self):
        '''Returns the port upon which this service listens.
        '''
        return self._port if self._port is not None else 80

    @property
    def protocol(self):
        '''Returns the protocol with which to communicate with this Service.
        '''
        return self._protocol if self._protocol is not None else 'HTTP'

    @property
    def container(self):
        '''Returns the docker image name for this k8s Service. Useful when creating
        Deployment objects.
        '''
        return self._container_name

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
        '''
        Returns total number of times to attempt calling this service, including retries.
        i.e. `total_attempts == 1` implies zero retries, `total_attempts == 3` implies two
        retries.
        '''
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
        self._namespace_shared = False
        self._id_hash = None
        self._retry_total_attempts = 2
        self._is_recoverable = False
        self._is_reliable_transport = False
        self._traffic_shadow_svc = None
        self._xgw_expression_type = 'feel'
        if annotations is not None:
            if 'rexflow' in annotations:
                self.update(annotations['rexflow'])

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
    def is_reliable_transport(self):
        return self._is_reliable_transport

    @property
    def traffic_shadow_svc(self):
        return self._traffic_shadow_svc

    @property
    def xgw_expression_type(self):
        return self._xgw_expression_type

    def update(self, annotations):
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
            self._is_recoverable = (annotations['recoverable'] or self.is_reliable_transport)

        if 'retry' in annotations:
            if 'total_attempts' in annotations['retry']:
                self._retry_total_attempts = annotations['retry']['total_attempts']

        if 'reliable_transport' in annotations:
            assert annotations['reliable_transport'] == 'kafka'
            self._is_reliable_transport = True
            self._is_recoverable = True

        if 'id_hash' in annotations:
            self._id_hash = annotations['id_hash']

        if 'traffic_shadow_svc' in annotations:
            assert not self._is_reliable_transport, "Shadowing traffic not allowed in Reliable WF"
            shadow_annots = annotations['traffic_shadow_svc']
            svc_annots = shadow_annots['service']

            if 'call' in shadow_annots:
                if 'path' in shadow_annots['call']:
                    path = shadow_annots['call']['path']
                else:
                    path = '/'
            if not path.startswith('/'):
                path = '/' + path

            proto = svc_annots.get('protocol', 'http')
            self._traffic_shadow_svc = {}
            k8s_url = f'{proto}://{svc_annots["host"]}.{svc_annots["namespace"]}:'
            k8s_url += f'{svc_annots["port"]}{path}'

            envoy_host = f'{svc_annots["host"]}.{svc_annots["namespace"]}.svc.cluster.local'
            envoy_cluster = f'outbound|{svc_annots["port"]}||{envoy_host}'

            self._traffic_shadow_svc = {
                'path': path,
                'k8s_url': k8s_url,
                'envoy_cluster': envoy_cluster,
            }

        if 'xgw_expression_type' in annotations:
            assert annotations['xgw_expression_type'] in VALID_XGW_EXPRESSION_TYPES
            self._xgw_expression_type = annotations['xgw_expression_type']


class BPMNComponent:
    '''
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
    '''
    def __init__(self,
                 spec: OrderedDict,
                 process: OrderedDict,
                 workflow_properties: WorkflowProperties):
        self.id = spec['@id']

        annotations = [a for a in list(get_annotations(process, self.id)) if 'rexflow' in a]
        assert len(annotations) == 1, \
            "Must provide exactly one 'rexflow' annotation for each BPMN Component"

        self._annotation = annotations[0]['rexflow']

        # Set default values. The constructors of child classes may override these values.
        # For example, a BPMNTask that calls a preexisting microservice should override
        # the value `self._is_preexisting`.
        self._is_preexisting = False
        self._is_in_shared_ns = workflow_properties.namespace_shared
        self._namespace = workflow_properties.namespace
        self._health_properties = HealthProperties()
        self._service_properties = ServiceProperties()
        self._call_properties = CallProperties()
        self._global_props = workflow_properties
        self._proc = process
        self._kafka_topics = []

        if 'preexisting' in self._annotation:
            self._is_preexisting = self._annotation['preexisting']

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

        if 'call' in self._annotation:
            self._call_properties.update(self._annotation['call'])
        if 'health' in self._annotation:
            self._health_properties.update(self._annotation['health'])
        if 'service' in self._annotation:
            self._service_properties.update(self._annotation['service'])

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
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
        raise NotImplementedError("Method must be overriden.")

    @property
    def namespace(self) -> str:
        '''Returns the k8s namespace in which the corresponding k8s deployment for this
        BPMNComponent sits.
        '''
        return self._namespace

    @property
    def is_in_shared_ns(self) -> bool:
        '''Returns True if the k8s object corresponding to this BPMNComponent sits in
        a shared k8s namespace, as opposed to a namespace that is dedicated solely
        to this Workflow Deployment.
        '''
        return self._is_in_shared_ns

    @property
    def is_preexisting(self) -> bool:
        '''Returns True if the k8s object corresponding to this BPMNComponent was
        deployed separately from the Workflow; i.e. it was pre-existing.
        '''
        return self._is_preexisting

    @property
    def health_properties(self) -> HealthProperties:
        '''Returns the HealthProperties object for this BPMNComponent.
        '''
        return self._health_properties

    @property
    def call_properties(self) -> CallProperties:
        '''Returns the CallProperties object for this BPMNComponent.
        '''
        return self._call_properties

    @property
    def service_properties(self) -> ServiceProperties:
        '''Returns the ServiceProperties object for this BPMNComponent.
        '''
        return self._service_properties

    @property
    def workflow_properties(self) -> WorkflowProperties:
        '''Returns the WorkflowProperties object for this BPMNComponent.
        '''
        return self._global_props

    @property
    def transport_kafka_topic(self) -> str:
        if not self.workflow_properties.is_reliable_transport:
            return None
        return f'{self.id}-kafka-{self._global_props.id_hash}'.replace('_', '-').lower()

    @property
    def k8s_url(self) -> str:
        '''Returns the fully-qualified host + path that is understood by the k8s
        kube-dns. For example, returns "http://my-service.my-namespace:my-port"
        '''
        service_props = self.service_properties
        proto = service_props.protocol.lower()
        host = service_props.host
        port = service_props.port
        return f'{proto}://{host}.{self.namespace}:{port}{self.path}'

    @property
    def envoy_host(self) -> str:
        '''Returns the Envoy-readable hostname for this service, for example
        "my-service.my-namespace.svc.cluster.local"
        '''
        service_props = self.service_properties
        host = service_props.host
        return f'{host}.{self.namespace}.svc.cluster.local'

    @property
    def kafka_topics(self) -> List[str]:
        return self._kafka_topics

    @property
    def annotation(self) -> dict:
        '''Returns the python dictionary representation of the rexflow annotation on the
        BPMN diagram for this BPMNComponent.'''
        return self._annotation

    @property
    def path(self) -> str:
        '''Returns the HTTP Path to call this component. The path refers to calling
        the BPMN component, and NOT the healthcheck.
        '''
        call_props = self.call_properties
        path = call_props.path
        if not path.startswith('/'):
            path = '/' + path
        return path
