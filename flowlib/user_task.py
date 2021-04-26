'''
Implements the BPMNUserTask class, which inherits from BPMNComponent.
'''

from collections import OrderedDict
from typing import Any, Mapping, List

from flowlib.bpmn_util import (
    BPMNComponent,
    HealthProperties,
    ServiceProperties,
    CallProperties,
    WorkflowProperties,
    get_annotations,
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

        # Convention is to use underscore for unused values.
        for _, text in get_annotations(process, self.id):
            if 'rexflow' in text and 'fields' in text['rexflow'] and 'desc' in text['rexflow']['fields']:
                self.field_desc = text['rexflow']['fields']['desc']
                break

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        return []
