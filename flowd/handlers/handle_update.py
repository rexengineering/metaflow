from flowlib import flow_pb2, workflow
from flowlib.config import INGRESS_TEMPLATE
from flowlib.constants import flow_result
from flowlib.ingress_utils import (
    get_current_occupant,
    switch_ingress,
    set_ingress,
    delete_ingress,
)


def handler(request: flow_pb2.StopRequest):
    if INGRESS_TEMPLATE is None:
        return flow_result(-1, "Ingress not enabled for this deployment.")
    result = dict()
    if request.action == flow_pb2.expose_ingress:
        wf_obj = workflow.Workflow.from_id(request.wf_id)

        # Check if the host is already taken.
        current_occupant_id = get_current_occupant(request.host)  # type: workflow.Workflow
        if current_occupant_id is not None:
            current_occupant = workflow.Workflow.from_id(current_occupant_id)
            assert request.switch_from_wf_id == current_occupant.id, \
                f"Host {request.host} already occuppied by {current_occupant.id}; " +\
                "use --force_switch_from"
            result = switch_ingress(request.host, wf_obj, current_occupant, request.args)
        else:
            result = set_ingress(request.host, wf_obj, request.args)
    elif request.action == flow_pb2.delete_ingress:
        current_occupant_id = get_current_occupant(request.host)  # type: workflow.Workflow
        assert current_occupant_id == request.wf_id, "provided host and wf id don't match."
        current_occupant = workflow.Workflow.from_id(current_occupant_id)
        result = delete_ingress(current_occupant)
    else:
        raise NotImplementedError('Lazy developer error!')

    return result
