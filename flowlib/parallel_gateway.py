'''
Implements the BPMNParallelGateway object, which inherits BPMNComponent.
'''

from collections import OrderedDict
import json
from typing import Any, Mapping, Set

from . import config, constants
from .bpmn_util import BPMNComponent
from .k8s_utils import create_deployment, create_service, create_serviceaccount


class BPMNParallelGateway(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, gateway: OrderedDict, process: OrderedDict, global_props=None):
        super().__init__(gateway, process, global_props)

        # Defer computing these properties until we have a digraph...
        self.forward_componentids = []
        self.forward_componentid = None
        self.incoming_call_count = 0

        self._gateway = gateway

        assert 'service' not in self.annotation, 'service-name must be auto-inferred for parallel gateways'
        self._service_properties.update(dict(
            host=f'{config.PGATEWAY_SVC_PREFIX}-{self.name}',
            port=config.PGATEWAY_LISTEN_PORT,
        ))

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: Mapping[str, Set[str]], sequence_flow_table: Mapping[str, Any]) -> list:
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

        service_name = self.service_properties.host
        dns_safe_name = service_name.replace('_', '-')
        port = self.service_properties.port

        in_vertices = [component_map[in_vertex] for in_vertex, vertices in digraph.items() if self.id in vertices]
        out_vertices = [component_map[out_vertex] for out_vertex in digraph[self.id]]
        # TODO: Make the merge mode a possible annotation for the gateway.
        merge_mode: int = int(constants.Parallel.MergeModes.OBJECT)
        if self.workflow_properties.use_closure_transport:
            merge_mode = int(constants.Parallel.MergeModes.UPDATE)
        env_config = [
            {
                'name': constants.Parallel.GatewayVars.INCOMING_IDS,
                'value': json.dumps([vertex.id for vertex in in_vertices])
            },
            {
                'name': constants.Parallel.GatewayVars.INCOMING_URLS,
                'value': json.dumps([vertex.k8s_url for vertex in in_vertices])
            },
            {
                'name': constants.Parallel.GatewayVars.FORWARD_IDS,
                'value': json.dumps([vertex.id for vertex in out_vertices])
            },
            {
                'name': constants.Parallel.GatewayVars.FORWARD_URLS,
                'value': json.dumps([vertex.k8s_url for vertex in out_vertices])
            },
            {'name': constants.Parallel.GatewayVars.MERGE_MODE, 'value': merge_mode},
        ]

        k8s_objects.append(create_serviceaccount(self._namespace, dns_safe_name))
        k8s_objects.append(create_service(self._namespace, dns_safe_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            dns_safe_name,
            config.PGW_IMAGE,
            port,
            env_config,
        ))

        return k8s_objects
