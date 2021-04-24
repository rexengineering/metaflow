'''
Implements the BPMNUserTask class, which inherits from BPMNComponent.
'''
import json
import logging

from collections import OrderedDict
from flowlib.config import UI_BRIDGE_NAME, UI_BRIDGE_INIT_PATH, UI_BRIDGE_PORT
from typing import Any, Mapping

from flowlib.bpmn_util import BPMNComponent, WorkflowProperties, get_annotations

class BPMNUserTask(BPMNComponent):
    def __init__(self, user_task: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(user_task, process, global_props)
        self._user_task = user_task

        # TODO: Maybe use `self.service_properties.update()` here? No worries if not...I'm
        # not too much of a stickler about stuff like this
        self.service_properties._host = UI_BRIDGE_NAME
        self.service_properties._port = UI_BRIDGE_PORT
        self.call_properties._path = UI_BRIDGE_INIT_PATH
        self.field_desc = None

        for annot,text in get_annotations(process, self.id):
            if 'rexflow' in text and 'fields' in text['rexflow'] and 'desc' in text['rexflow']['fields']:
                self.field_desc = text['rexflow']['fields']['desc']
                break

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        # TODO?
        return []
