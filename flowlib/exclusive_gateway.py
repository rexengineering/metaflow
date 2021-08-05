'''
Implements the BPMNXGateway object, which inherits BPMNComponent.
'''

from collections import OrderedDict
import json
from typing import Mapping

from .bpmn_util import BPMNComponent, outgoing_sequence_flow_table, get_edge_transport, Bpmn
from .reliable_wf_utils import create_kafka_transport
from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_deployment_affinity,
)

from .config import (
    XGW_IMAGE,
    XGW_LISTEN_PORT,
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
    DMN_SERVER_HOST
)

XGATEWAY_SVC_PREFIX = "xgateway"


class BPMNXGateway(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, gateway: OrderedDict, process: OrderedDict=None, global_props=None):
        super().__init__(gateway, process, global_props)
        self.expression = ""
        self._gateway = gateway
        self._branches = []

        self._service_properties.update({
            "port": XGW_LISTEN_PORT,
            "host": self.name,
        })

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent],
                      digraph: OrderedDict, edge_map: OrderedDict) -> list:
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
        default_path = None
        conditional_paths = []
        self.outgoing_edges = outgoing_sequence_flow_table(self._proc)[self.id]
        for edge in self.outgoing_edges:
            transport_type = get_edge_transport(edge, self.workflow_properties.transport)
            assert transport_type in ['kafka', 'rpc'], \
                f"transport_type {transport_type} not implemented for xgw."
            if Bpmn.condition_expression in edge:
                bpmn_component = component_map[edge['@targetRef']]
                expr = edge[Bpmn.condition_expression]['#text']
                if transport_type == 'kafka':
                    transport = create_kafka_transport(self, bpmn_component)
                    self.kafka_topics.append(transport.kafka_topic)
                    k8s_objects.extend(transport.k8s_specs)
                    k8s_url = f'http://{transport.envoy_host}:{transport.port}{transport.path}'
                    conditional_paths.append({
                        'type': self._global_props.xgw_expression_type,
                        'expression': expr,
                        'component_id': bpmn_component.id,  # equivalent to edge['@targetRef']
                        'k8s_url': k8s_url,
                        'total_attempts': transport.total_attempts,
                    })
                elif transport_type == 'rpc':
                    conditional_paths.append({
                        'type': self._global_props.xgw_expression_type,
                        'expression': expr,
                        'component_id': bpmn_component.id,  # equivalent to edge['@targetRef']
                        'k8s_url': bpmn_component.k8s_url,
                        'total_attempts': bpmn_component.call_properties.total_attempts,
                    })
            else:
                assert default_path is None, "Can only have one default path for XGW."
                default_component = component_map[edge['@targetRef']]
                if transport_type == 'rpc':
                    default_path = {
                        "component_id": edge['@targetRef'],  # equivalent to default_component.id
                        "k8s_url": default_component.k8s_url,
                        "total_attempts": default_component.call_properties.total_attempts,
                    }
                elif transport_type == 'kafka':
                    transport = create_kafka_transport(self, default_component)
                    self.kafka_topics.append(transport.kafka_topic)
                    k8s_objects.extend(transport.k8s_specs)
                    default_path = {
                        "component_id": bpmn_component.id,
                        "k8s_url":
                            f"http://{transport.envoy_host}:{transport.port}{transport.path}",
                        "total_attempts": transport.total_attempts,
                    }

        # Note: we may or may not take this out for FEEL...
        assert default_path is not None, "Must have a default path"

        # TODO: Work with Jon to see what a BPMN document would look like with more than
        # two outgoing edges from a BPMN diagram.
        assert len(conditional_paths) == 1, "Not implemented."

        # Add k8s specs for the actual XGW
        service_name = self.service_properties.host
        port = self.service_properties.port

        env_config = self.init_env_config() + \
        [
            {
                'name': 'REXFLOW_XGW_FAIL_URL',
                'value': 'http://flowd.rexflow:9002/instancefail'
            },
            # TODO: (?) move the following two env vars to a k8s configMap, and mount as a file
            # on the XGW container. Could be too much data for env vars in a non-trivial
            # future use-case. Or, it might be fine as-is. Not sure.
            {
                'name': 'REXFLOW_XGW_CONDITIONAL_PATHS',
                'value': json.dumps(conditional_paths),
            },
            {
                'name': 'REXFLOW_XGW_DEFAULT_PATH',
                'value': json.dumps(default_path),
            }
        ]
        if self._global_props.xgw_expression_type == 'feel':
            assert DMN_SERVER_HOST is not None, "Must provide DMN_SERVER_HOST for FEEL evaluation"
            env_config.append({
                "name": "DMN_SERVER_HOST",
                "value": DMN_SERVER_HOST,
            })

        if self._global_props.traffic_shadow_url:
            env_config.append({
                "name": "KAFKA_SHADOW_URL",
                "value": self._global_props.traffic_shadow_url,
            })

        k8s_objects.append(create_serviceaccount(self._namespace, service_name))
        k8s_objects.append(create_service(self._namespace, service_name, port))
        k8s_objects.append(create_deployment(
            self._namespace,
            service_name,
            XGW_IMAGE,
            port,
            env_config,
            health_props=self.health_properties,
        ))
        return k8s_objects
