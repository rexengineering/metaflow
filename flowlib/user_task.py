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
from flowlib.bpmn_util import (
    BPMNComponent,
    HealthProperties,
    ServiceProperties,
    CallProperties,
    WorkflowProperties,
    get_annotations,
)
from flowlib.k8s_utils import (
    create_deployment,
    create_service,
    create_rexflow_ingress_vs,
)


class BPMNUserTask(BPMNComponent):
    def __init__(self, user_task: OrderedDict, process: OrderedDict, global_props: WorkflowProperties,
        service_props: ServiceProperties, call_props: CallProperties, health_props: HealthProperties = None
    ):
        super().__init__(user_task, process, global_props)
        self._user_task = user_task

        self._service_properties = service_props
        self._call_properties = call_props
        if health_props is not None:
            self._health_properties = health_props
        self.field_desc = None

        for annot, text in get_annotations(process, self.id):
            if 'rexflow' in text and 'fields' in text['rexflow'] and 'desc' in text['rexflow']['fields']:
                self.field_desc = text['rexflow']['fields']['desc']
                break

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        return []
