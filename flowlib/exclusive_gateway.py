'''
Implements the BPMNXGateway object, which inherits BPMNComponent.
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
    get_annotations,
    CallProperties,
    ServiceProperties,
    HealthProperties,
    BPMNComponent,
)


XGATEWAY_SVC_PREFIX = "xgateway"
XGATEWAY_LISTEN_PORT = "5000"


class BPMNXGateway(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, gateway : OrderedDict, process : OrderedDict=None, global_props=None):
        super().__init__(gateway, process, global_props)
        self.jsonpath = ""
        self.operator = ""
        self.comparison_value = ""
        self.true_forward_componentid = None
        self.false_forward_componentid = None
        self._gateway = gateway

        assert 'jsonpath' in self._annotation, "XGateway: Must specify jsonpath to compare."
        assert 'value' in self._annotation, "XGatewway: Must specify `value` to compare to."
        assert 'operator' in self._annotation, "XGatewway: Must specify `operator` (==, <, >)"

        self.jsonpath = self.annotation['jsonpath']
        self.comparison_value = self.annotation['value']
        self.operator = self.annotation['operator']
        assert self.operator in ['==', '<', '>'], "XGatewway: Must specify `operator` (==, <, >)"

        # We've got the annotation. From here, let's find out the name of the resulting
        # gateway service.
        self.name = f"{XGATEWAY_SVC_PREFIX}-{self.annotation['gateway_name']}"
        assert ('service' not in self.annotation), "service-name must be auto-inferred for X-Gateways"

        self._service_properties.update({
            "port": XGATEWAY_LISTEN_PORT,
            "host": self.name,
        })

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
        # First, use the component_map and digraph to figure out what needs to be sent to where
        true_next_cookie = self.annotation['gateway_true']['next_step']
        false_next_cookie = self.annotation['gateway_false']['next_step']

        # Look at the digraph to find out the two possible next steps. Then check the annotations
        # for each of the steps to see which we go to for "true" evaluations and which we go to
        # for "false" evaluations.
        outgoing_calls = digraph[self.id]
        assert len(outgoing_calls) == 2  # for now, XGateways only implement binary choice.

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

        # Ok, now we're ready to go for creating k8s specs.
        k8s_objects = []

        service_name = self.service_properties.host
        dns_safe_name = service_name.replace('_', '-')
        port = self.service_properties.port
        
        # SVC Account
        service_account = {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {
                'name': dns_safe_name,
            },
        }
        k8s_objects.append(service_account)

        # SVC
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

        # K8s Deployment. This is the tricky part, since we must use the Environment
        # variables to configure the behavior of the exclusive gateway service.
        # component_map[self.true_forward_componentid].k8s_url,
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
                                    {'name': 'REXFLOW_XGW_JSONPATH', 'value': self.jsonpath},
                                    {'name': 'REXFLOW_XGW_OPERATOR', 'value': self.operator},
                                    {'name': 'REXFLOW_XGW_COMPARISON_VALUE', 'value': self.comparison_value},
                                    {
                                        'name': 'REXFLOW_XGW_TRUE_URL',
                                        'value': component_map[self.true_forward_componentid].k8s_url,
                                    },
                                    {
                                        'name': 'REXFLOW_XGW_FALSE_URL',
                                        'value': component_map[self.false_forward_componentid].k8s_url,
                                    },
                                ]
                            },
                        ],
                    },
                },
            },
        }
        k8s_objects.append(deployment)
        if self._namespace is not None:
            service_account['metadata']['namespace'] = self._namespace
            service['metadata']['namespace'] = self._namespace
            deployment['metadata']['namespace'] = self._namespace

        return k8s_objects