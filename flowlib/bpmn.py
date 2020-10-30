'''Utility library for working with BPMN documents.
'''

from collections import OrderedDict
from io import IOBase
import logging
import socket
import subprocess
import sys
from typing import Any, Iterator, List, Mapping, Optional, Set

import yaml
import xmltodict

from .envoy_config import get_envoy_config, Upstream
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


# TODO: Dammit colt this is ugly.
# TODO: Cache, please?
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


class BPMNTask:
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict=None, global_props=None):
        self._task = task
        self._proc = process
        self._global_props = global_props
        self.id = task['@id'] # type: str
        self.name = task['@name'] # type: str
        self._url = '' # type: str
        # FIXME: This is Zeebe specific.  Need to provide override if coming from
        # some other modeling tool. -- note from Jon
        service_name = task['bpmn:extensionElements']['zeebe:taskDefinition']['@type']
        self.definition = ComponentProperties(service_name)
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
        if not self._url:
            definition = self.definition
            service_props = definition.service
            proto = service_props.protocol.lower()
            host = service_props.host
            if self._global_props and self._global_props.orchestrator != 'docker':
                host += f'.{self._global_props.namespace}.svc.cluster.local'
            port = service_props.port
            call_props = definition.call
            path = call_props.path
            if not path.startswith('/'):
                path = '/' + path
            self._url = f'{proto}://{host}:{port}{path}'
        return self._url


XGATEWAY_SVC_PREFIX = "xgateway"
XGATEWAY_LISTEN_PORT = "5000"

class BPMNXGateway:
    '''Wrapper for BPMN Exclusive Gateway metadata.
    '''
    def __init__(self, gateway : OrderedDict, process : OrderedDict=None, global_props=None):
        self.jsonpath = ""
        self.operator = ""
        self.comparison_value = ""
        self.true_forward_componentid = None
        self.false_forward_componentid = None

        self._gateway = gateway
        self._proc = process
        self._global_props = global_props
        self.id = gateway['@id'] # type: str
        self._url = '' # type: str

        # FIXME: This is Zeebe specific.  Need to provide override if coming from
        # some other modeling tool.
        self.annotations = []
        if not self._proc:
            raise "You must properly annotate your Exclusive gateway!"

        # Here, we iterate through all of the annotations in the BPMN Doc to find the magic
        # one that 
        targets = [  # `targets` has to do with annotation targets (the dotted lines from text box to component)
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
        rexflow_annotations = [annotation for annotation in self.annotations if 'rexflow' in annotation]
        assert len(rexflow_annotations) == 1
        self.annotation = self.annotations[0]['rexflow']
        self.jsonpath = self.annotation['jsonpath']
        self.comparison_value = self.annotation['value']
        self.operator = self.annotation['operator']

        # We've got the annotation. From here, let's find out the name of the resulting
        # gateway service.
        self.name = f"{XGATEWAY_SVC_PREFIX}-{self.annotation['gateway_name']}"
        self.definition = ComponentProperties(self.name)
        assert ('service' not in self.annotation), "service-name must be auto-inferred for X-Gateways"

        self.definition.update({
            "service": {
                "host": self.name,
                "port": XGATEWAY_LISTEN_PORT,
            }
        })

        # Ok, now we know what to call our service (for k8s deployment) AND how to deploy it. TODO's are:
        # 1. Figure out what the URL's are for the next two steps in service (using the )
        # 2. Store the conditional decision config in ETCD.

        true_next_cookie = self.annotation['gateway_true']['next_step']
        false_next_cookie = self.annotation['gateway_false']['next_step']
        # Look at the digraph to find out the two possible next steps. Then check the annotations
        # for each of the steps to see which we go to for "true" evaluations and which we go to
        # for "false" evaluations.
        raw_graph = raw_proc_to_digraph(self._proc)  # FIXME: save this computation. Don't do it over-and-over.
        outgoing_calls = raw_graph[self.id]

        # now we find annotations...pardon the copy-pasta. Just for now...
        outgoing_component_targets = {
            association['@targetRef']: association['@sourceRef']
            for association in iter_xmldict_for_key(self._proc, 'bpmn:association')
            if association['@sourceRef'] in outgoing_calls
        }
        for annotation in iter_xmldict_for_key(self._proc, 'bpmn:textAnnotation'):
            if (annotation['@id'] not in outgoing_component_targets.keys()) or not annotation['bpmn:text'].startswith('rexflow:'):
                continue
            annot_dict = yaml.safe_load(annotation['bpmn:text'].replace('\xa0', ''))['rexflow']
            if 'next_step_id' in annot_dict:
                if annot_dict['next_step_id'] == true_next_cookie:
                    assert not self.true_forward_componentid
                    self.true_forward_componentid = outgoing_component_targets[annotation['@id']]
                if annot_dict['next_step_id'] == false_next_cookie:
                    assert not self.false_forward_componentid
                    self.false_forward_componentid = outgoing_component_targets[annotation['@id']]
        assert self.true_forward_componentid
        assert self.false_forward_componentid

    @property
    def url(self):
        '''
        Returns the K8s FQDN for the resulting XGateway (once it's deployed in
        the istio cluster)
        '''
        if not self._url:
            definition = self.definition
            service_props = definition.service
            proto = service_props.protocol.lower()
            host = service_props.host
            if self._global_props and self._global_props.orchestrator != 'docker':
                host += f'.{self._global_props.namespace}.svc.cluster.local'
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


class ComponentProperties:
    '''
    Shared struct-like class used to store information about a BPMN Component's
    representation that gets deployed into our cluster.

    As a reminder, the initial
    REXFlow prototype will say that "Every Component is a Service", i.e. a Task,
    a Throw Event, a Catch Event, Mux/DMux Gateways, and Conditional Gateways all
    will be implemented by a k8s Service.

    This class contains info about how to make calls to that service.
    '''
    def __init__(self, service_name):
        self.service_name = service_name
        self._name = None
        self.service = ServiceProperties(service_name)
        self.call = CallProperties()
        self.health = HealthProperties()

    @property
    def name(self) -> str:
        return self._name if self._name is not None else self.service_name

    def update(self, annotations : Mapping[str, Any]) -> None:
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
    def __init__(self, tasks:Optional[List[BPMNTask]]=None):
        if tasks is None:
            tasks = [] # type: List[BPMNTask]
        self.tasks = tasks
        self.task_map = {task.id : task for task in tasks} # type: Mapping[str, BPMNTask]

    def __len__(self):
        return len(self.tasks)

    def __iter__(self) -> Iterator[BPMNTask]:
        return iter(self.tasks)

    def __getitem__(self, key):
        return self.tasks.__getitem__(key)  # should this be tasks_map.__getitem__ ?


class BPMNXGateways:
    '''Utility container for BPMNExclusiveGateway instances.
    '''
    def __init__(self, gateways:Optional[List[BPMNXGateway]]=None):
        if gateways is None:
            gateways = [] # type: List[BPMNXGateway]
        self.gateways = gateways
        # type---map of {str: BPMNXGateway}
        self.gateway_map = {gateway.id : gateway for gateway in gateways}

    def __len__(self):
        return len(self.gateways)

    def __iter__(self) -> Iterator[BPMNXGateway]:
        return iter(self.gateways)

    def __getitem__(self, key):
        return self.gateways.__getitem__(key)  # should this be gateway_map.__getitem__?


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
        return self._orchestrator if self._orchestrator is not None else 'docker'

    def update(self, annotations):
        if 'orchestrator' in annotations:
            self._orchestrator = annotations['orchestrator']
        if 'namespace' in annotations:
            self._namespace = annotations['namespace']


class BPMNProcess:
    def __init__(self, process : OrderedDict):
        self.namespace = "default"  # FIXME
        self._process = process
        self.id = process['@id']
        entry_point = process['bpmn:startEvent']
        assert isinstance(entry_point, OrderedDict)
        self.entry_point =  entry_point
        self.exit_point = process['bpmn:endEvent']
        self.annotations = list(self.get_annotations(self.entry_point['@id']))
        self.properties = WorkflowProperties(self.annotations)
        self.xgateways = BPMNXGateways([
            BPMNXGateway(gateway, process, self.properties)
            for gateway in iter_xmldict_for_key(process, 'bpmn:exclusiveGateway')
        ])
        self.tasks = BPMNTasks([
            BPMNTask(task, process, self.properties)
            for task in iter_xmldict_for_key(process, 'bpmn:serviceTask')
        ])
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
    def digraph(self) -> Mapping[str, Set[str]]:
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

    def get_namespace(self, id_hash:str = None):
        namespace = self.properties.namespace
        if ((namespace != 'default') and (id_hash is not None) and (len(id_hash) > 3)):
            namespace = f'{namespace}-{id_hash[:4]}'
        return namespace

    def _generate_http_url(self, component_id: str):
        '''Accepts a component id, which may be for a serviceTask or a gateway
        at this point. Returns the fqdn for that component. This is the python
        request module-friendly URL.

        # FIXME: this is bad design...do something more elegant.
        '''
        # FIXME: don't be so lazy, dammit
        namespace = "default"
        if component_id in self.tasks.task_map:
            task = self.tasks.task_map[component_id]
            defn = task.definition
            name = defn.name.replace('_', '-') # FIXME: ...
            fqdn = f'{name}.{namespace}'
            return f'http://{fqdn}:{defn.service.port}'
        if component_id in self.xgateways.gateway_map:
            task = self.xgateways.gateway_map[component_id]
            defn = task.definition
            name = defn.name.replace('_', '-') # FIXME: ...
            fqdn = f'{name}.{namespace}'
            return f'http://{fqdn}:{defn.service.port}'

        # FIXME: we pray that it's intended for a "STOP" event. We can check to
        # make sure, but I haven't gotten there yet.
        return "http://flowd.rexflow:9002"

    def generate_kubernetes(self, id_hash:str = None):
        results = []
        namespace = self.get_namespace(id_hash)
        if namespace == 'default':
            namespace = None
        else:
            results.append(
                {
                    'apiVersion': 'v1',
                    'kind': 'Namespace',
                    'metadata': {
                        'name', namespace,
                    },
                }
            )
        
        for xgw in self.xgateways:
            definition = xgw.definition
            service_name = definition.name
            # FIXME: The following is a workaround; need to add a full-on regex
            # check of the service name and error on invalid spec.
            dns_safe_name = service_name.replace('_', '-')
            port = definition.service.port
            service_account = {
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'name': dns_safe_name,
                },
            }
            results.append(service_account)
            service = {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': dns_safe_name,
                    'labels': {
                        'app': dns_safe_name,
                    },
                },
                'spec': {
                    'ports': [
                        {
                            'name': 'http',
                            'port': port,
                            'targetPort': port,
                        }
                    ],
                    'selector': {
                        'app': dns_safe_name,
                    },
                },
            }
            results.append(service)
            deployment = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': dns_safe_name,
                },
                'spec': {
                    'replicas': 1, # FIXME: Make this a property one can set in the BPMN.
                    'selector': {
                        'matchLabels': {
                            'app': dns_safe_name,
                        },
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': dns_safe_name,
                            },
                        },
                        'spec': {
                            'serviceAccountName': dns_safe_name,
                            'containers': [
                                {
                                    'image': 'exclusive-gateway:1.0.0',
                                    'imagePullPolicy': 'IfNotPresent',
                                    'name': dns_safe_name,
                                    'ports': [
                                        {
                                            'containerPort': port,
                                        },
                                    ],
                                    'env': [
                                        {'name': 'REXFLOW_XGW_JSONPATH', 'value': xgw.jsonpath},
                                        {'name': 'REXFLOW_XGW_OPERATOR', 'value': xgw.operator},
                                        {'name': 'REXFLOW_XGW_COMPARISON_VALUE', 'value': xgw.comparison_value},
                                        {'name': 'REXFLOW_XGW_TRUE_URL', 'value': self._generate_http_url(xgw.true_forward_componentid)},
                                        {'name': 'REXFLOW_XGW_FALSE_URL', 'value': self._generate_http_url(xgw.false_forward_componentid)},
                                    ]
                                },
                            ],
                        },
                    },
                },
            }
            results.append(deployment)
            if namespace is not None:
                service_account['metadata']['namespace'] = namespace
                service['metadata']['namespace'] = namespace
                deployment['metadata']['namespace'] = namespace
        
        for task in self.tasks:
            definition = task.definition
            service_name = definition.name
            # FIXME: The following is a workaround; need to add a full-on regex
            # check of the service name and error on invalid spec.
            dns_safe_name = service_name.replace('_', '-')
            port = definition.service.port
            service_account = {
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'name': dns_safe_name,
                },
            }
            results.append(service_account)
            service = {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': dns_safe_name,
                    'labels': {
                        'app': dns_safe_name,
                    },
                },
                'spec': {
                    'ports': [
                        {
                            'name': 'http',
                            'port': port,
                            'targetPort': port,
                        }
                    ],
                    'selector': {
                        'app': dns_safe_name,
                    },
                },
            }
            results.append(service)
            deployment = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': dns_safe_name,
                },
                'spec': {
                    'replicas': 1, # FIXME: Make this a property one can set in the BPMN.
                    'selector': {
                        'matchLabels': {
                            'app': dns_safe_name,
                        },
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': dns_safe_name,
                            },
                        },
                        'spec': {
                            'serviceAccountName': dns_safe_name,
                            'containers': [
                                {
                                    'image': definition.service.container,
                                    'imagePullPolicy': 'IfNotPresent',
                                    'name': dns_safe_name,
                                    'ports': [
                                        {
                                            'containerPort': port,
                                        },
                                    ],
                                },
                            ],
                        },
                    },
                },
            }
            results.append(deployment)
            if namespace is not None:
                service_account['metadata']['namespace'] = namespace
                service['metadata']['namespace'] = namespace
                deployment['metadata']['namespace'] = namespace
        return results

    def to_kubernetes(self, stream:IOBase = None, id_hash:str = None, **kws):
        if stream is None:
            stream = sys.stdout
        results = self.generate_kubernetes(id_hash)
        # FIXME: Add Envoy sidecars to Kubernetes results.
        result = yaml.safe_dump_all(results, **kws)
        stream.write(result)
        return result

    def _make_forward(self, upstream : Upstream):
        return {
            'name': upstream.name,
            'cluster': upstream.name,
            'host': upstream.host,
            'port': upstream.port,
            'path': '/', # FIXME: Add path to Upstream NamedTuple...
            'method': 'POST', # FIXME: Add method to Upstream NamedTuple...
        }

    def generate_istio(self, kube_specs : List[Mapping[str, Any]]):
        '''Patches sidecar configurations with BAVS/JAMS rerouting data.
        '''
        namespace = 'default'
        task_map = {}
        for task in self.tasks:
            # FIXME: Per above...
            dns_safe_name = task.definition.name.replace('_', '-')
            task_map[dns_safe_name] = {'task': task}
        for kube_spec in kube_specs:
            spec_name = kube_spec['metadata']['name']
            if spec_name not in task_map:
                continue
            spec_kind = kube_spec['kind']
            if spec_kind == 'Namespace':
                namespace = kube_spec['name']
            elif spec_kind == 'ServiceAccount':
                task_map[spec_name]['service_account'] = kube_spec
            elif spec_kind == 'Service':
                task_map[spec_name]['service'] = kube_spec
            elif spec_kind == 'Deployment':
                task_map[spec_name]['deployment'] = kube_spec
            # elif spec_name in self.xgateways:
            #     if spec_kind == 'Namespace':
            #         namespace = kube_spec['name']
            #     elif spec_kind == 'ServiceAccount':
            #         task_map[spec_name]['service_account'] = kube_spec
            #     elif spec_kind == 'Service':
            #         task_map[spec_name]['service'] = kube_spec
            #     elif spec_kind == 'Deployment':
            #         task_map[spec_name]['deployment'] = kube_spec
            # else:
            #     assert False

        # We ONLY need to iterate through the task_map, since the task_map represents
        # every serviceTask. The serviceTasks are microservices (written by WF Engine user)
        # which each get their own networking.istio.io/v1alpha3.EnvoyFilter object.
        # The Gateways and other Components don't get their own EnvoyFilter objects, so we
        # DONT want to iterate through them here.
        for service_name in task_map:
            specs = task_map[service_name]
            task = specs['task'] # type: BPMNTask
            # FIXME: Remove exposure to the ingress gateway.  However, this is
            # currently useful for debugging purposes.
            uri_prefix = (f'/{service_name}' if namespace == 'default'
                          else f'/{namespace}/{service_name}')
                
            port = specs['service']['spec']['ports'][0]['port']
            service_fqdn = (service_name if namespace == 'default'
                            else f'{service_name}.{namespace}.svc.cluster.local')
            kube_specs.append({
                'apiVersion': 'networking.istio.io/v1alpha3',
                'kind': 'VirtualService',
                'metadata': {
                    'name': service_name,
                    'namespace': 'default',
                },
                'spec': {
                    'hosts': ['*'],
                    'gateways': ['rexflow-gateway'],
                    'http': [
                        {
                            'match': [{'uri': {'prefix': uri_prefix}}],
                            'rewrite': {'uri': '/'},
                            'route': [
                                {
                                    'destination': {
                                        'port': {'number': port},
                                        'host': service_fqdn
                                    }
                                }
                            ]
                        }
                    ]
                }
            })
            # Now generate the EnvoyFilter...
            upstreams = [] # type: List[Upstream]
            for out_edge in self.digraph.get(task.id, set()):
                if out_edge in self.tasks.task_map:
                    out_task = self.tasks.task_map[out_edge] # type: BPMNTask
                    out_defn = out_task.definition
                    out_name = out_defn.name.replace('_', '-') # FIXME: ...
                    out_fqdn = f'{out_name}.{namespace}.svc.cluster.local'
                    upstreams.append(
                        Upstream(
                            out_name,
                            out_fqdn,
                            out_defn.service.port
                        )
                    )
                elif out_edge in self.xgateways.gateway_map:
                    out_gw = self.xgateways.gateway_map[out_edge]
                    out_defn = out_gw.definition
                    out_name = out_defn.name.replace('_', '-')
                    out_fqdn = f'{out_name}.{namespace}.svc.cluster.local'
                    upstreams.append(
                        Upstream(
                            out_name,
                            out_fqdn,
                            out_defn.service.port
                        )
                    )
                else:
                    # FIXME: We just pray that this means we've got an "End" event.
                    # FIXME: Get FQDN and port number from whatever is running
                    # the flowd server...
                    # SOAPBOX: We're also going to have to have a serious discussion
                    # about namespaces. Does each WF Deployment get its own namespace?
                    # That's my (Colt's) vote. Also, we need to test what Jon did with
                    # namespaces so far, and verify that it works.
                    upstreams.append(
                        Upstream(
                            'flowd',
                            'flowd.rexflow.svc.cluster.local',
                            9002
                        )
                    )
            bavs_config = {
                'forwards': [
                    self._make_forward(upstream) for upstream in upstreams
                ],
            }
            kube_specs.append({
                'apiVersion': 'networking.istio.io/v1alpha3',
                'kind': 'EnvoyFilter',
                'metadata': {
                    'name': f'hijack-{service_name}',
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
            })

    def to_istio(self, stream:IOBase = None, id_hash:str = None, **kws):
        result = None
        if stream is None:
            stream = sys.stdout
        results = self.generate_kubernetes(id_hash)
        self.generate_istio(results)

        # This code below does manual sidecar injection. It is ONLY necessary
        # for dev on docker-desktop, since it is not easily feasible to
        # configure d4d istio to automatically inject a custom image.
        # On a true deployment (where we set imagePullSecrets), we
        # could easily tell Istio to automatically inject our own custom
        # proxy image, and thus remove the code below.
        temp_yaml = yaml.safe_dump_all(results, **kws)
        istioctl_result = subprocess.run(
            ['istioctl', 'kube-inject', '-f', '-'],
            input=temp_yaml, capture_output=True, text=True,
        )
        if istioctl_result.returncode == 0:
            result = istioctl_result.stdout.replace(': Always', ': IfNotPresent'
                ).replace('docker.io/istio/proxyv2:1.7.1', 'rex-proxy:1.7.1')
            stream.write(result)
        else:
            logging.error(f'Error from Istio:\n{istioctl_result.stderr}')
        return result
