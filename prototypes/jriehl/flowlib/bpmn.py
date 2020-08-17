'''Utility library for working with BPMN documents.
'''

from collections import OrderedDict
from io import IOBase, StringIO
import logging
import subprocess
import sys

import yaml
import xmltodict

from .etcd_utils import get_etcd


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


def get_tasks(process, wrap=False):
    '''Given a BPMN process, get the service tasks in that process.
    Arguments:
        process - OrderedDict instance containing a BPMN process.
        wrap -  Flag to wrap the task OrderedDict instances as BPMNTask instances.
    Returns:
        List of OrderedDict or BPMNTask instances for each service task.
    '''
    return list(BPMNTask(task, process) if wrap else task
                for task in iter_xmldict_for_key(process, 'bpmn:serviceTask'))


class BPMNTask:
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict=None):
        self._task = task
        self._proc = process
        self.id = task['@id']
        self.name = task['@name']
        self._url = None
        # FIXME: This is Zeebe specific.  Need to provide override if coming from
        # some other modeling tool.
        service_name = task['bpmn:extensionElements']['zeebe:taskDefinition']['@type']
        self.definition = TaskProperties(service_name)
        self.annotations = []
        if self._proc:
            targets = [
                association['@targetRef']
                for association in iter_xmldict_for_key(self._proc, 'bpmn:association')
                if association['@sourceRef'] == self.id
            ]
            self.annotations = [
                yaml.safe_load(annotation['bpmn:text'].replace('\xa0', ''))
                for annotation in iter_xmldict_for_key(self._proc, 'bpmn:textAnnotation')
                if annotation['@id'] in targets and
                    annotation['bpmn:text'].startswith('rexflow:')
            ]
            for annotation in self.annotations:
                if 'rexflow' in annotation:
                    self.definition.update(annotation['rexflow'])

    @property
    def url(self):
        if self._url is None:
            definition = self.definition
            service_props = definition.service
            proto = service_props.protocol.lower()
            host = service_props.host
            port = service_props.port
            call_props = definition.call
            path = call_props.path
            if not path.startswith('/'):
                path = '/' + path
            self._url = f'{proto}://{host}:{port}{path}'
        return self._url


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
    def path(self):
        return self._path if self._path is not None else '/'

    @property
    def method(self):
        return self._method if self._method is not None else 'POST'

    @property
    def serialization(self):
        return self._serialization if self._serialization is not None else 'JSON'

    def update(self, annotations):
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
    def path(self):
        return self._path if self._path is not None else '/'

    @property
    def method(self):
        return self._method if self._method is not None else 'GET'

    @property
    def period(self):
        return self._period if self._period is not None else 10

    @property
    def response(self):
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


class TaskProperties:
    def __init__(self, service_name):
        self.service_name = service_name
        self._name = None
        self.service = ServiceProperties(service_name)
        self.call = CallProperties()
        self.health = HealthProperties()

    @property
    def name(self):
        return self._name if self._name is not None else self.service_name

    def update(self, annotations):
        if 'name' in annotations:
            self._name = annotations['name']
        if 'service' in annotations:
            self.service.update(annotations['service'])
        if 'call' in annotations:
            self.call.update(annotations['call'])
        if 'health' in annotations:
            self.health.update(annotations['health'])


class BPMNTasks:
    '''Utility container for BPMNTask instances.
    '''
    def __init__(self, tasks=None):
        if tasks is None:
            tasks = []
        self.tasks = tasks
        self.task_map = {task.id : task for task in tasks}

    def __len__(self):
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks)

    def __getitem__(self, key):
        return self.tasks.__getitem__(key)

    def to_docker(self, stream : IOBase = None, **kws):
        if stream is None:
            stream = sys.stdout
        services = {}
        result = {'version' : '3', 'services' : services}
        for task in self.tasks:
            definition = task.definition
            service = {}
            services[definition.name] = service
            service['image'] = definition.service.container
            port = definition.service.port
            service['ports'] = [f'{port}:{port}']
            service['deploy'] = {'replicas':1, 'restart_policy':{'condition':'on-failure'}}
        return yaml.safe_dump(result, stream, **kws)

    def to_kubernetes(self, stream : IOBase = None):
        if stream is None:
            stream = sys.stdout
        result = {}
        raise NotImplementedError('Lazy developer!')
        return yaml.safe_dump(result, stream)

    def to_istio(self, stream : IOBase = None):
        if stream is None:
            stream = sys.stdout
        result = {}
        raise NotImplementedError('Lazy developer!')
        return yaml.safe_dump(result, stream)


class WorkflowProperties:
    def __init__(self, annotations=None):
        self._orchestrator = None
        if annotations is not None:
            for annotation in annotations:
                if 'rexflow' in annotation:
                    self.update(annotation['rexflow'])

    @property
    def orchestrator(self):
        return self._orchestrator if self._orchestrator is not None else 'docker'

    def update(self, annotations):
        if 'orchestrator' in annotations:
            self._orchestrator = annotations['orchestrator']


class BPMNProcess:
    def __init__(self, process : OrderedDict):
        self._process = process
        self.id = process['@id']
        self.tasks = BPMNTasks([
            BPMNTask(task, process)
            for task in iter_xmldict_for_key(process, 'bpmn:serviceTask')
        ])
        entry_point = process['bpmn:startEvent']
        assert isinstance(entry_point, OrderedDict)
        self.entry_point =  entry_point
        self.exit_point = process['bpmn:endEvent']
        self.annotations = list(self.get_annotations(self.entry_point['@id']))
        self.properties = WorkflowProperties(self.annotations)
        self._digraph = None

    @classmethod
    def from_workflow_id(cls, workflow_id):
        etcd = get_etcd(is_not_none=True)
        process_xml = etcd.get(f'/rexflow/workflows/{workflow_id}/proc')[0]
        process_dict = xmltodict.parse(process_xml)['bpmn:process']
        process = cls(process_dict)
        return process

    def to_xml(self):
        return xmltodict.unparse(OrderedDict([('bpmn:process', self._process)]))

    def to_digraph(self, digraph : dict=None):
        if digraph is None:
            digraph = dict()
        for sequence_flow in iter_xmldict_for_key(self._process, 'bpmn:sequenceFlow'):
            source_ref = sequence_flow['@sourceRef']
            target_ref = sequence_flow['@targetRef']
            if source_ref not in digraph:
                digraph[source_ref] = set()
            digraph[source_ref].add(target_ref)
        return digraph

    @property
    def digraph(self):
        if self._digraph is None:
            result = self.to_digraph()
            self._digraph = result
        else:
            result = self._digraph
        return result

    def get_annotations(self, source_ref=None):
        if source_ref is not None:
            targets = set()
            for association in iter_xmldict_for_key(self._process, 'bpmn:association'):
                if source_ref is None or association['@sourceRef'] == source_ref:
                    targets.add(association['@targetRef'])
        else:
            targets = None
        for annotation in iter_xmldict_for_key(self._process, 'bpmn:textAnnotation'):
            if targets is None or annotation['@id'] in targets:
                text = annotation['bpmn:text']
                if text.startswith('rexflow:'):
                    yield yaml.safe_load(text.replace('\xa0', ''))
