"""
Implements the BPMNUserTask class, which inherits from BPMNComponent.
"""
import logging

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
from flowlib.constants import UserTaskPersistPolicy


class BPMNUserTask(BPMNComponent):
    def __init__(self, user_task: OrderedDict, 
                process: OrderedDict, 
                global_props: WorkflowProperties,
                service_props: ServiceProperties, 
                call_props: CallProperties, 
                health_props: HealthProperties = None
    ):
        super().__init__(user_task, process, global_props)
        self._user_task = user_task

        self._service_properties = service_props
        self._call_properties = call_props
        if health_props is not None:
            self._health_properties = health_props
        self.field_desc = None

        # setup persistance option. See if there is a local option, if so use that value.
        # otherwise, examine any global option. We're looking for a simple true/false here
        # to know if we need to persist for this specific user task.
        self._persist_user_data = global_props.user_task_persist_policy == UserTaskPersistPolicy.PERSIST_EACH

        for _, text in get_annotations(process, self.id):
            # we're just looking for the rexflow annotation
            if 'rexflow' in text:
                if 'post_to_salesforce' in text['rexflow']:
                    self._persist_user_data = text['rexflow']['post_to_salesforce']
                if 'fields' in text['rexflow'] and 'desc' in text['rexflow']['fields']:
                    self.field_desc = text['rexflow']['fields']['desc']
                break

    def to_kubernetes(self, id_hash, component_map: Mapping[str, Any],
                      digraph: OrderedDict, sequence_flow_table: Mapping[str, Any]) -> list:
        return []

    @property
    def persist_user_data(self):
        return self._persist_user_data

    @property
    def field_description(self):
        return self.field_desc
