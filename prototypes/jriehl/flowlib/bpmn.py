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


class TaskProperties:
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
        return self.tasks.__getitem__(key)


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
        self._process = process
        self.id = process['@id']
        entry_point = process['bpmn:startEvent']
        assert isinstance(entry_point, OrderedDict)
        self.entry_point =  entry_point
        self.exit_point = process['bpmn:endEvent']
        self.annotations = list(self.get_annotations(self.entry_point['@id']))
        self.properties = WorkflowProperties(self.annotations)
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

    def to_docker(self, stream : IOBase = None, **kws):
        if stream is None:
            stream = sys.stdout
        services = {}
        networks = {}
        result = {
            'version' : '3',
            'services' : services,
            'networks' : networks,
        }
        for task in self.tasks:
            definition = task.definition
            service_name = definition.name
            port = definition.service.port
            network_name = f'{service_name}_net'
            services[service_name] = {
                'image' : definition.service.container,
                'ports' : [5000], # FIXME: Need to add container-specific port
                                  # as a service property here.
                'deploy' : {
                    'replicas' : 1,
                    'restart_policy' : {
                        'condition' : 'on-failure',
                    },
                },
                'networks' : {
                    network_name : {
                        'aliases': [service_name],
                    },
                },
            }
            networks[network_name] = {}
            proxy_name = f'{service_name}_proxy'
            upstreams = []
            for out_edge in self.digraph.get(task.id, set()):
                logging.debug(out_edge)
                if out_edge in self.tasks.task_map:
                    out_task = self.tasks.task_map[out_edge]
                    out_defn = out_task.definition
                    upstreams.append(Upstream(
                        out_defn.name,
                        socket.getfqdn(), # FIXME: shouldn't this have something
                                          # to do with out_defn.service.host?
                        out_defn.service.port))
                else:
                    # FIXME: Get port number from whatever is running the flowd
                    # Flask server...
                    upstreams.append(Upstream('flowd', socket.getfqdn(), 9002))
            envoy_config = get_envoy_config(service_name, set(upstreams))
            logging.info(f'Wrote Envoy config for {service_name} to {envoy_config}')
            services[proxy_name] = {
                'image' : 'envoyproxy/envoy-dev:latest',
                'ports' : [f'{port}:5000'], # FIXME: See note above about adding
                                            # container port.
                'networks' : [
                    'default',
                    network_name,
                ],
                'volumes' : [
                    f'{envoy_config}:/etc/envoy/envoy.yaml',
                ]
            }
        result_yaml = yaml.safe_dump(result, **kws)
        logging.debug(f'Docker result_yaml:\n{result_yaml}')
        stream.write(result_yaml)
        return result_yaml

    def get_namespace(self, id_hash:str = None):
        namespace = self.properties.namespace
        if ((namespace != 'default') and (id_hash is not None) and (len(id_hash) > 3)):
            namespace = f'{namespace}-{id_hash[:4]}'
        return namespace

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
            spec_kind = kube_spec['kind']
            spec_name = kube_spec['metadata']['name']
            if spec_kind == 'Namespace':
                namespace = kube_spec['name']
            elif spec_kind == 'ServiceAccount':
                task_map[spec_name]['service_account'] = kube_spec
            elif spec_kind == 'Service':
                task_map[spec_name]['service'] = kube_spec
            elif spec_kind == 'Deployment':
                task_map[spec_name]['deployment'] = kube_spec
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
                else:
                    # FIXME: Get FQDN and port number from whatever is running
                    # the flowd server...
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
