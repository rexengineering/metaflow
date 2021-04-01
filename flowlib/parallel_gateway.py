

'''
Implements the BPMNParallelGateway object, which inherits BPMNComponent.
'''

from collections import OrderedDict, namedtuple
from io import IOBase
from typing import Any, Iterator, List, Mapping, Optional, Set

import json
import logging
import socket
import subprocess
import sys

import yaml
import xmltodict

from flowlib import config

from .k8s_utils import create_deployment, create_service, create_serviceaccount

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


logging.basicConfig(level=logging.INFO)


class BPMNParallelGateway(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, gateway: OrderedDict, process: OrderedDict=None, global_props=None):

        if process is None:
            process = OrderedDict()

        super().__init__(gateway, process, global_props)
        self.forward_componentids = []
        self.forward_componentid = None
        self.incoming_call_count = 0
        self._gateway = gateway

        if not self._proc:
            raise ValueError("You must properly annotate your parallel gateway!")

        self.gateway_type = self._annotation['gateway_type']

        # We've got the annotation. From here, let's find out the name of the resulting
        # gateway service.
        self.name = f"{config.PGATEWAY_SVC_PREFIX}-{self._annotation['gateway_name']}"
        assert ('service' not in self._annotation), "service-name must be auto-inferred for parallel gateways"

        self._service_properties.update({
            'port': config.PGATEWAY_LISTEN_PORT,
            'host': self.name,
        })

        # Ok, now we know what to call our service (for k8s deployment) AND how to deploy it. TODO's are:
        # 1. Figure out what the URL's are for the next steps in service
        # 2. Store the config in env vars for the deployment
        # Both of these things will be done in the to_kubernetes() function.

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph: OrderedDict) -> list:
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

        if self.gateway_type == 'splitter':
            # First, use the component_map and digraph to figure out what needs to be sent to where
            next_cookies = self._annotation['gateway_split']

            # Look at the digraph to find out the two possible next steps. Then check the annotations
            # for each of the steps to see which we go to for "true" evaluations and which we go to
            # for "false" evaluations.
            outgoing_calls = digraph[self.id]
            assert len(outgoing_calls) >= 2  # splitter PGateways only make sense if there are at least two endpoints

            outgoing_component_targets = {
                association['@targetRef']: association['@sourceRef']
                for association in iter_xmldict_for_key(self._proc, 'bpmn:association')
                if association['@sourceRef'] in outgoing_calls
            }

            for annotation in iter_xmldict_for_key(self._proc, 'bpmn:textAnnotation'):

                if (annotation['@id'] not in outgoing_component_targets.keys()) or not annotation['bpmn:text'].startswith('rexflow:'):
                    continue

                annot_dict = yaml.safe_load(annotation['bpmn:text'].replace('\xa0', ''))['rexflow']
                next_step_id = annot_dict.get('next_step_id')

                if next_step_id:

                    if next_step_id in next_cookies:
                        outgoing_component_target = outgoing_component_targets[annotation['@id']]
                        assert outgoing_component_target not in self.forward_componentids
                        self.forward_componentids.append(outgoing_component_target)

        elif self.gateway_type == 'combiner':

            # look at the digraph to find out the next step

            outgoing_calls = digraph[self.id]
            assert len(outgoing_calls) == 1  # for now, combiner PGateways only implement one outgoing endpoint.

            for start_id, end_ids in digraph.items():
                if self.id in end_ids:
                    self.incoming_call_count += 1

            outgoing_component_targets = {
                association['@targetRef']: association['@sourceRef']
                for association in iter_xmldict_for_key(self._proc, 'bpmn:association')
                if association['@sourceRef'] in outgoing_calls
            }

            logging.info(f"outgoing_component_targets = {outgoing_component_targets}")

            for annotation in iter_xmldict_for_key(self._proc, 'bpmn:textAnnotation'):
                logging.info(f"annotation = {annotation}")

                #`if (annotation['@id'] not in outgoing_component_targets.keys()) or not annotation['bpmn:text'].startswith('rexflow:'):
                if (annotation['@id'] not in outgoing_component_targets.keys()):
                    continue

                annot_dict = yaml.safe_load(annotation['bpmn:text'].replace('\xa0', ''))['rexflow']

                logging.info(f"annot_dict = {annot_dict}")

                assert not self.forward_componentid
                self.forward_componentid = outgoing_component_targets[annotation['@id']]

            assert self.forward_componentid

        else:
            assert False, f"Unrecognized gateway type '{self.gateway_type}'"

        # Ok, now we're ready to go for creating k8s specs.

        k8s_objects = []

        service_name = self.service_properties.host
        dns_safe_name = service_name.replace('_', '-')
        port = self.service_properties.port

        forward_urls = []

        for outgoing_component_target in self.forward_componentids:
            forward_urls.append(component_map[outgoing_component_target].k8s_url)

        forward_url = config.FLOWD_URL

        if self.forward_componentid:
            forward_url = component_map[self.forward_componentid].k8s_url

        env_config = [
            {'name': 'REXFLOW_PGW_TYPE', 'value': self.gateway_type},
            {'name': 'REXFLOW_PGW_INCOMING_COUNT', 'value': self.incoming_call_count},
            {'name': 'REXFLOW_PGW_FORWARD_URL', 'value': forward_url},
            {'name': 'REXFLOW_PGW_FORWARD_ID', 'value': self.forward_componentid},
            {'name': 'REXFLOW_PGW_FORWARD_URLS', 'value': json.dumps(forward_urls)},
            {'name': 'REXFLOW_PGW_FORWARD_IDS', 'value': json.dumps(self.forward_componentids)},
        ]

        k8s_objects.append(create_serviceaccount(self._namespace, dns_safe_name))
        k8s_objects.append(create_service(self._namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            dns_safe_name,
            'parallel-gateway:1.0.0',
            port,
            env_config,
        ))

        return k8s_objects