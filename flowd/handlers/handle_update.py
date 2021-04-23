import yaml

from flowlib import flow_pb2, workflow
from flowlib.config import INGRESS_TEMPLATE
from flowlib.constants import flow_result
from flowlib.ingress_utils import (
    get_current_occupant,
    set_ingress,
    delete_ingress,
)


def handler(request: flow_pb2.StopRequest):
    result = {}
    updates = yaml.safe_load_all(request.update_spec)

    for update_spec in updates:
        if update_spec['action'] == 'expose_ingress':
            result[f'expose_{update_spec["host"]}'] = set_ingress(
                update_spec['host'],
                update_spec['wf_id'],
                component_name=update_spec.get('component_name'),
                component_id=update_spec.get('component_id'),
                args=update_spec.get('args'),
            )
        elif update_spec['action'] == 'clear_ingress':
            result[f'clear_{update_spec["host"]}'] = delete_ingress(
                update_spec['host'],
                update_spec['wf_id'],
                update_spec.get('component_name'),
                update_spec.get('component_id'),
            )
        elif update_spec['action'] == 'subscribe_to_topic':
            raise NotImplementedError("Lazy Developer Error!")
        elif update_spec['action'] == 'unsubscribe_from_topic':
            raise NotImplementedError("Lazy Developer Error!")
        else:
            raise NotImplementedError("Provided action not supported.")

    return result
