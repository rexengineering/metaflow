'''Utilities used in bpmn.py.
'''
from collections import OrderedDict
from typing import Any, Iterator, List, Mapping, Optional, Set
import yaml
import xmltodict


def iter_xmldict_for_key(odict : OrderedDict, key : str):
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
    def __init__(self, service_name):
        self.name = service_name
        self._host = None
        self._port = None
        self._protocol = None
        self._container = None

    @property
    def host(self):
        return self._host if self._host is not None else self.name

    @property
    def port(self):
        return self._port if self._port is not None else 80

    @property
    def protocol(self):
        return self._protocol if self._protocol is not None else 'HTTP'

    @property
    def container(self):
        return self._container if self._container is not None else self.name

    def update(self, annotations):
        if 'host' in annotations:
            self._host = annotations['host']
        if 'port' in annotations:
            self._port = int(annotations['port'])
        if 'orchestrator' in annotations:
            self._orchestrator = annotations['orchestrator']
        if 'protocol' in annotations:
            self._protocol = annotations['protocol']
        if 'container' in annotations:
            self._container = annotations['container']


class CallProperties:
    def __init__(self):
        self._path = None
        self._method = None
        self._serialization = None

    @property
    def path(self) -> str:
        return self._path if self._path is not None else '/'

    @property
    def method(self) -> str:
        return self._method if self._method is not None else 'POST'

    @property
    def serialization(self) -> str:
        return self._serialization if self._serialization is not None else 'JSON'

    def update(self, annotations:Mapping[str, Any]) -> None:
        if 'path' in annotations:
            self._path = annotations['path']
        if 'method' in annotations:
            self._method = annotations['method']
        if 'serialization' in annotations:
            self._serialization = annotations['serialization']


class HealthProperties:
    def __init__(self):
        self._path = None
        self._method = None
        self.query = None
        self._period = None
        self._response = None

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


class WorkflowProperties:
    def __init__(self, annotations=None):
        self._orchestrator = None
        self._namespace = None
        if annotations is not None:
            for annotation in annotations:
                if 'rexflow' in annotation:
                    self.update(annotation['rexflow'])

    @property
    def namespace(self):
        return self._namespace if self._namespace is not None else 'default'

    @property
    def orchestrator(self):
        assert self._orchestrator == 'istio'
        return self._orchestrator if self._orchestrator is not None else 'docker'

    def update(self, annotations):
        if 'orchestrator' in annotations:
            assert annotations['orchestrator'] == 'istio'
            self._orchestrator = annotations['orchestrator']
        if 'namespace' in annotations:
            self._namespace = annotations['namespace']


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
    def __init__(self, component: OrderedDict, process : OrderedDict, workflow_properties : WorkflowProperties):
        pass

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any], digraph: OrderedDict) -> list:
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

    #@property
    def namespace(self) -> str:
        raise NotImplementedError("Method must be overriden.")

    #@property
    def health_properties(self) -> HealthProperties:
        raise NotImplementedError("Method must be overriden.")

    #@property
    def call_properties(self) -> CallProperties:
        raise NotImplementedError("Method must be overriden.")

    #@property
    def service_properties(self) -> ServiceProperties:
        raise NotImplementedError("Method must be overriden.")

    #@property
    def k8s_url(self) -> str:
        '''Returns the fully-qualified host + path that is understood by the k8s
        kube-dns. For example, returns "http://my-service.my-namespace:my-port"
        '''
        service_props = self.service_properties()
        proto = service_props.protocol.lower()
        host = service_props.host
        port = service_props.port
        return f'{proto}://{host}.{self.namespace()}:{port}{self.path()}'

    #@property
    def envoy_host(self) -> str:
        '''Returns the Envoy Cluster Name for this service, for example
        "my-service.my-namespace.svc.cluster.local"
        '''
        service_props = self.service_properties()
        host = service_props.host
        return f'{host}.{self.namespace()}.svc.cluster.local'

    #@property
    def path(self) -> str:
        '''Returns the HTTP Path for this component.
        '''
        call_props = self.call_properties()
        path = call_props.path
        if not path.startswith('/'):
            path = '/' + path
        return path

    @property
    def url(self):
        service_props = self.service_properties()
        proto = service_props.protocol.lower()
        host = service_props.host
        host += f'.{self.namespace()}.svc.cluster.local'
        port = service_props.port
        call_props = self.call_properties()
        path = call_props.path
        if not path.startswith('/'):
            path = '/' + path
        return f'{proto}://{host}:{port}{path}'
