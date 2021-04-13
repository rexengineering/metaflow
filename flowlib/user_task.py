'''
Implements the BPMNUserTask class, which inherits from BPMNComponent.
'''

from collections import OrderedDict
from typing import Any, Mapping

from flowlib.bpmn_util import BPMNComponent, WorkflowProperties


class BPMNUserTask(BPMNComponent):
    def __init__(self, user_task: OrderedDict, process: OrderedDict, global_props: WorkflowProperties):
        super().__init__(user_task, process, global_props)
        self._user_task = user_task

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        # TODO?
        return []
