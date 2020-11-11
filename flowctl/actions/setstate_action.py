import argparse
import logging

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection
from flowlib.constants import BStates

__help__ = '(DEBUG) Force a deployment or instance into a specific state.'

# flowctl setstate _state_for_kind_ (INSTANCE|DEPLOYMENT) (deployment_id ...|instance_id ...)

def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('state', type=str,
        help='The target state. Must be apropos for the provided KIND.'
    )
    parser.add_argument('kind', default='INSTANCE',
        help=f'Request kind, one of {", ".join(key for key in flow_pb2.RequestKind.keys())}, default is INSTANCE.',
    )
    parser.add_argument('ids', nargs='+', type=str,
        help='Specific workflow deployment or instance ID\'s to modify.'
    )
    return parser


def setstate_action (namespace : argparse.Namespace, *args, **kws):
    response = None
    kind = getattr(flow_pb2.RequestKind, namespace.kind, flow_pb2.RequestKind.INSTANCE)
    state = namespace.state.encode('utf-8')
    logging.info(f'setstate_action {state} {kind} {namespace.ids} {type(state)} {type(kind)} {type(namespace.ids)}')
    # Validate that the requested state is apropos for the provided kind
    if kind == flow_pb2.RequestKind.DEPLOYMENT:
        if state not in {BStates.STARTING, BStates.RUNNING, BStates.STOPPING, BStates.STOPPED, BStates.ERROR}:
            raise ValueError(f'{state} is not a valid state for kind {namespace.kind}.')
    elif kind == flow_pb2.RequestKind.INSTANCE:
        if state not in {BStates.STARTING, BStates.RUNNING, BStates.STOPPING, BStates.STOPPED, BStates.COMPLETED, BStates.ERROR}:
            raise ValueError(f'{state} is not a valid state for kind {namespace.kind}.')
    else:
        # not really possible, since we have a default of INSTANCE
        raise ValueError(f'{namespace.kind} is not a valid kind. Use DEPLOYMENT or INSTANCE.')

    # if we get here, we know that the kind and the state for the kind is valid. So do the work.
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        response = flowd.SetState(flow_pb2.SetStateRequest(
            state=state, kind=kind, ids=namespace.ids
        ))
    status = response.status
    if status < 0:
        logging.error(
            f'Error from server: {response.status}, "{response.message}"'
        )
    else:
        logging.info(
            f'Got response: {response.status}, "{response.message}", {response.data}'
        )

    # return status
