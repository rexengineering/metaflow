'''
Implements the BPMNTask object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
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
from .bpmn_util import (
    iter_xmldict_for_key,
    CallProperties,
    ServiceProperties,
    HealthProperties,
    BPMNComponent,
)


Upstream = namedtuple('Upstream', ['name', 'host', 'port', 'path', 'method'])


class BPMNTask(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict, global_props):
        self._namespace = global_props.namespace
        self._task = task
        self._proc = process
        self._global_props = global_props
        self.id = task['@id'] # type: str
        self.name = task['@name'] # type: str
        self._url = '' # type: str
        # FIXME: This is Zeebe specific.  Need to provide override if coming from
        # some other modeling tool. -- note from Jon
        service_name = task['bpmn:extensionElements']['zeebe:taskDefinition']['@type']

        self._service_properties = ServiceProperties(service_name)
        self._call_properties = CallProperties()
        self._health_properties = HealthProperties()

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
        else:
            raise "Argh, somehow we didn't pass in a BPMN Process to this Task. Yuck!"
        for annotation in self.annotations:
            if 'rexflow' in annotation:
                rexflow = annotation['rexflow']
                if 'service' in rexflow:
                    self._service_properties.update(rexflow['service'])
                if 'call' in rexflow:
                    self._call_properties.update(rexflow['call'])
                if 'health' in rexflow:
                    self._health_properties.update(rexflow['health'])

    #@property
    def health_properties(self) -> HealthProperties:
        return self._health_properties

    #@property
    def call_properties(self) -> CallProperties:
        return self._call_properties

    #@property
    def service_properties(self) -> ServiceProperties:
        return self._service_properties

    #@property
    def namespace(self) -> str:
        return self._namespace

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph : OrderedDict) -> list:
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

        # k8s ServiceAccount
        service_name = self.service_properties().name
        # FIXME: The following is a workaround; need to add a full-on regex
        # check of the service name and error on invalid spec.
        dns_safe_name = service_name.replace('_', '-')
        port = self.service_properties().port
        namespace = self._namespace
        service_account = {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {
                'name': dns_safe_name,
            },
        }
        k8s_objects.append(service_account)

        uri_prefix = (f'/{service_name}' if namespace == 'default' else f'/{namespace}/{service_name}')
        service_fqdn = (dns_safe_name if namespace == 'default'
                        else f'{dns_safe_name}.{namespace}.svc.cluster.local')
        # VirtualService
        # (I'm not sure why, but Jon had it in his code)
        virtual_service = {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'VirtualService',
            'metadata': {
                'name': dns_safe_name,
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
        }
        k8s_objects.append(virtual_service)

        # k8s Service
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
        k8s_objects.append(service)

        # k8s Deployment
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
                                'image': self.service_properties().container,
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
        k8s_objects.append(deployment)

        # Now...the EnvoyFilters
        upstreams = [] # type: list[Upstream]
        forward_set = digraph.get(self.id, set())
        for forward in forward_set:
            bpmn_component = component_map[forward] # type: BPMNComponent
            path = bpmn_component.call_properties().path
            if not path.startswith('/'):
                path = '/' + path
            upstreams.append(
                Upstream(
                    bpmn_component.service_properties().name,
                    bpmn_component.envoy_host(),
                    bpmn_component.service_properties().port,
                    path,
                    bpmn_component.call_properties().method,
                )
            )
        bavs_config = {
            'forwards': [
                self._make_forward(upstream) for upstream in upstreams
            ],
        }
        envoy_filter = {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'EnvoyFilter',
            'metadata': {
                'name': f'hijack-{dns_safe_name}',
                'namespace': namespace,
            },
            'spec': {
                'workloadSelector': {'labels': {'app': dns_safe_name}},
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
        k8s_objects.append(envoy_filter)

        if self._global_props.namespace is not None:
            service_account['metadata']['namespace'] = self._global_props.namespace
            service['metadata']['namespace'] = self._global_props.namespace
            deployment['metadata']['namespace'] = self._global_props.namespace

        return k8s_objects

    def _make_forward(self, upstream : Upstream):
        return {
            'name': upstream.name,
            'cluster': upstream.name,
            'host': upstream.host,
            'port': upstream.port,
            'path': upstream.path,
            'method': upstream.method, # TODO: Test with methods other than POST
        }