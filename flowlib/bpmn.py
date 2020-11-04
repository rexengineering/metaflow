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

from .etcd_utils import get_etcd
from .task import BPMNTask
from .exclusive_gateway import BPMNXGateway
from .start_event import BPMNStartEvent
from .end_event import BPMNEndEvent
# from .bpmn_throw import BPMNThrowEvent
# from .bpmn_catch import BPMNCatchEvent

from .bpmn_util import (
    iter_xmldict_for_key,
    raw_proc_to_digraph,
    get_annotations,
    parse_events,
    HealthProperties,
    CallProperties,
    ServiceProperties,
    BPMNComponent,
    WorkflowProperties,
)


class BPMNProcess:
    def __init__(self, process : OrderedDict):
        self.namespace = "default"  # TODO: Read from BPMN Spec
        self._process = process
        self.id = process['@id']
        entry_point = process['bpmn:startEvent']
        assert isinstance(entry_point, OrderedDict)  # TODO: verify that this means there's only 1 start event
        self.entry_point =  entry_point
        self.annotations = list(get_annotations(process, self.entry_point['@id']))
        self.properties = WorkflowProperties(self.annotations)

        # needed for calculation of some BPMN Components
        self._digraph = raw_proc_to_digraph(process)

        # Maps an Id (eg. "Event_25dst7" or "Gateway_2sh38s") to a BPMNComponent Object.
        self.component_map = {} # type: Mapping[str, BPMNComponent]

        # Now, create all of the BPMN Components.
        # Start with Tasks:
        self.tasks = []
        for task in iter_xmldict_for_key(process, 'bpmn:serviceTask'):
            bpmn_task = BPMNTask(task, process, self.properties)
            self.tasks.append(bpmn_task)
            self.component_map[task['@id']] = bpmn_task

        # Exclusive Gateways (conditional)
        self.xgateways = []
        for gw in iter_xmldict_for_key(process, 'bpmn:exclusiveGateway'):
            bpmn_gw = BPMNXGateway(gw, process, self.properties)
            self.xgateways.append(bpmn_gw)
            self.component_map[gw['@id']] = bpmn_gw

        # Don't forget BPMN Start Event!
        self.start_event = BPMNStartEvent(self.entry_point, process, self.properties)
        self.component_map[self.entry_point['@id']] = self.start_event

        # Don't forget BPMN End Events!
        # TODO: Test to make sure it works with multiple End Events.
        self.end_events = []
        for eev in iter_xmldict_for_key(process, 'bpmn:endEvent'):
            end_event = BPMNEndEvent(eev, process, self.properties)
            self.end_events.append(end_event)
            self.component_map[eev['@id']] = end_event

        self.all_components = []
        self.all_components.extend(self.tasks)
        self.all_components.extend(self.xgateways)

        # don't yet add start/end events to self.all_components because we don't want
        # healthchecks for them (they are just virtual components at this point)

        # # Throw Events.
        # # For now, to avoid forcing the user of REXFlow to have to annotate each event
        # # as either a Throw or Catch, we will infer based on the following rule:
        # # If there is an incoming edge to the Event in self.to_digraph, then
        # # it's a Throw event. Else, it's a Catch event.
        # self.throws = []
        # for event in iter_xmldict_for_key(process, 'bpmn:intermediateThrowEvent'):
        #     if 'bpmn:incoming' in event:
        #         bpmn_throw = BPMNThrowEvent(event, process, self.properties)
        #         self.throws.append(bpmn_throw)
        #         self.component_map[event['@id']] = bpmn_throw

        # self.catches = []
        # for event in iter_xmldict_for_key(process, 'bpmn:intermediateThrowEvent'):
        #     if 'bpmn:incoming' not in event:
        #         bpmn_catch = BPMNCatchEvent(event, process, self.properties)
        #         self.catches.append(bpmn_catch)
        #         self.component_map[event['@id']] = bpmn_catch

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

    def get_namespace(self, id_hash:str = None):
        namespace = self.properties.namespace
        if ((namespace != 'default') and (id_hash is not None) and (len(id_hash) > 3)):
            namespace = f'{namespace}-{id_hash[:4]}'
        return namespace

    def to_kubernetes(self, stream:IOBase = None, id_hash:str = None, **kws):
        # No longer used
        raise NotImplementedError("REXFlow requires Istio.")

    def to_istio(self, stream:IOBase = None, id_hash:str = None, **kws):
        if stream is None:
            stream = sys.stdout
        results = []
        for bpmn_component in self.component_map.keys():
            results.extend(
                self.component_map[bpmn_component].to_kubernetes(id_hash, self.component_map, self._digraph)
            )

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
