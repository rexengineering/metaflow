'''
Implements the BPMNUserTask class, which inherits from BPMNComponent.
'''
import json
import logging

from collections import OrderedDict
from typing import Any, Mapping, List

from flowlib.config import (
    DO_MANUAL_INJECTION,
    K8S_SPECS_S3_BUCKET,
    UI_BRIDGE_IMAGE,
    UI_BRIDGE_NAME,
    UI_BRIDGE_PORT,
    UI_BRIDGE_INIT_PATH,
    CREATE_DEV_INGRESS,
)
from flowlib.bpmn_util import BPMNComponent, WorkflowProperties
from flowlib.k8s_utils import (
    create_deployment,
    create_service,
    create_rexflow_ingress_vs,
)


class BPMNUserTask(BPMNComponent):
    def __init__(self, user_task: OrderedDict, process: OrderedDict, global_props: WorkflowProperties,
        all_user_tasks: List[OrderedDict], should_deploy=True
    ):
        super().__init__(user_task, process, global_props)
        self._user_task = user_task

        self._should_deploy = should_deploy

        self.service_properties.update({
            'host': UI_BRIDGE_NAME,
            'port': UI_BRIDGE_PORT,
        })
        self.call_properties.update({
            'path': UI_BRIDGE_INIT_PATH
        })
        self._all_user_tasks = all_user_tasks

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        if not self._should_deploy:
            return []

        results = []
        logging.info('Hoboy, user tasks detected, adding UI bridge to deployment.')

        user_tasks = [component_map[spec['@id']] for spec in self._all_user_tasks]

        bridge_config = {}
        for task in user_tasks:
            task_outbound_edges = set(digraph[task.id])
            task_outbound_components = [
                component_map[component_id] for component_id in task_outbound_edges
            ]
            bridge_config[task.id] = [
                {
                    'next_task_id_header': next_task.id,
                    'k8s_url': next_task.k8s_url,
                }
                for next_task in task_outbound_components
            ]

        ui_bridge_env = [
            {
                'name': 'WORKFLOW_DID',
                'value': self.namespace
            },
            {
                'name': 'WORKFLOW_TIDS',
                'value': ':'.join([task.id for task in user_tasks]),
            },
            {
                'name': 'BRIDGE_CONFIG',
                'value': json.dumps(bridge_config),
            }
        ]
        results.append(create_deployment(
            self.namespace,
            self.service_name,
            UI_BRIDGE_IMAGE,
            UI_BRIDGE_PORT,
            ui_bridge_env,
            etcd_access=True,
            use_service_account=False
        ))
        results.append(create_service(
            self.namespace,
            self.service_name,
            UI_BRIDGE_PORT,
        ))
        if CREATE_DEV_INGRESS:
            results.append(create_rexflow_ingress_vs(
                self.namespace,
                f'{self.service_name}-{self._global_props.id_hash}',
                f'/{self.namespace}-{self.service_name}',
                UI_BRIDGE_PORT,
                f'{UI_BRIDGE_NAME}.{self.namespace}.svc.cluster.local'
            ))
        return results
