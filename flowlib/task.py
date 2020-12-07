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
    WorkflowProperties,
    BPMNComponent,
    get_annotations,
    calculate_id_hash,
)

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
)


Upstream = namedtuple('Upstream', ['name', 'host', 'port', 'path', 'method', 'total_attempts'])


class BPMNTask(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict, global_props: WorkflowProperties):
        super().__init__(task, process, global_props)
        self._task = task

        assert 'service' in self._annotation, "Must annotate Service Task with service information."
        assert 'host' in self._annotation['service'], "Must annotate Service Task with service host."

        if self._is_preexisting:
            assert 'namespace' in self._annotation['service'], "Must provide namespace of preexisting service."
            self._namespace = self._annotation['service']['namespace']

    def _generate_envoyfilter(self, component_map: Mapping[str, BPMNComponent], digraph: OrderedDict) -> list:
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

        # We name the envoyfilter withhash if in a shared namespace and without hash
        # if it's not in a shared namespace, regardless of whether service is preexisting.
        # However, when the service is pre-existing, the service_properties.host does NOT
        # include the id_hash. Therefore, we must append the id_hash to envoyfilter name
        # IF the service is pre-existing.
        if self._is_preexisting:
            envoyfilter_name += '-' + self.workflow_properties.id_hash

        port = self.service_properties.port
        namespace = self._namespace  # namespace in which the k8s objects live.

        upstreams = [] # type: list[Upstream]
        forward_set = digraph.get(self.id, set())
        for forward in forward_set:
            bpmn_component = component_map[forward] # type: BPMNComponent
            path = bpmn_component.call_properties.path
            if not path.startswith('/'):
                path = '/' + path
            upstreams.append(
                Upstream(
                    bpmn_component.service_properties.host,
                    bpmn_component.envoy_host,
                    bpmn_component.service_properties.port,
                    path,
                    bpmn_component.call_properties.method,
                    bpmn_component.call_properties.total_attempts,
                )
            )
        bavs_config = {
            'forwards': [
                self._make_forward(upstream) for upstream in upstreams
            ],
            'wf_id': self._global_props.id,
            'flowd_envoy_cluster': 'outbound|9002||flowd.rexflow.svc.cluster.local',
            'flowd_path': '/instancefail',
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
        k8s_objects.append(self._generate_envoyfilter(component_map, digraph))
        if self._is_preexisting:
            return k8s_objects

        # Reminder: ServiceProperties.host() properly handles whether or not to include
        # id hash.
        service_name = self.service_properties.host
        dns_safe_name = service_name.replace('_', '-')

        # k8s ServiceAccount
        port = self.service_properties.port
        namespace = self._namespace
        assert self.namespace, "new-grad programmer error: namespace should be set by now."
        uri_prefix = (f'/{service_name}' if namespace == 'default' else f'/{namespace}/{service_name}')

        k8s_objects.append(create_serviceaccount(namespace, dns_safe_name))
        k8s_objects.append(create_service(namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            namespace,
            dns_safe_name,
            self.service_properties.container,
            port,
            env=[],
        ))
        k8s_objects.append(create_rexflow_ingress_vs(
            namespace,
            dns_safe_name,
            uri_prefix=uri_prefix,
            dest_port=port,
            dest_host=f'{dns_safe_name}.{namespace}.svc.cluster.local',
        ))

        return k8s_objects

    def _make_forward(self, upstream : Upstream):
        return {
            'name': upstream.name,
            'cluster': upstream.name,
            'host': upstream.host,
            'port': upstream.port,
            'path': upstream.path,
            'method': upstream.method, # TODO: Test with methods other than POST
            'total_attempts': upstream.total_attempts,
        }
