import argparse
import json
import logging
import os

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection


__help__ = 'query workflows or workflow instances'


def __refine_args__(parser: argparse.ArgumentParser):
    # it gets very boring typing out the KIND types, so defining some useful shorthands
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-k', '--kind', action='store', default='INSTANCE',
        help='Request kind, one of ' +  # noqa
             ', '.join(k for k in flow_pb2.RequestKind.keys()) +  # noqa
             'default is INSTANCE.',
    )
    group.add_argument(
        '-d', '--deployment', action='store_true',
        help='Shorthand to specify kind of type DEPLOYMENT.',
    )
    group.add_argument(
        '-i', '--instance', action='store_true',
        help='Shorthand to specify kind of type INSTANCE.',
    )
    parser.add_argument(
        '--kubernetes-output', action='store',
        help='File location to dump kubernetes spec. Valid only for -k DEPLOYMENT.'
    )
    # expand group with additional shorthands for new KIND types

    parser.add_argument(
        '-o',
        '--output',
        action='store_true',
        help='Output response data to stdout.'
    )
    parser.add_argument(
        'ids',
        nargs='*',
        type=str,
        help='Specific workflow deployment or instance ID\'s to query.'
    )
    return parser


def ps_action(namespace: argparse.Namespace, *args, **kws):
    response = None
    if namespace.kubernetes_output:
        include_kubernetes = True
    else:
        include_kubernetes = False
    if namespace.deployment:
        kind = flow_pb2.RequestKind.DEPLOYMENT
    elif namespace.instance:
        kind = flow_pb2.RequestKind.INSTANCE
    else:
        kind = getattr(flow_pb2.RequestKind, namespace.kind, flow_pb2.RequestKind.INSTANCE)
    with get_flowd_connection(namespace.flowd_host, namespace.flowd_port) as flowd:
        request = flow_pb2.PSRequest(
            kind=kind, ids=namespace.ids, include_kubernetes=include_kubernetes,
        )
        response = flowd.PSQuery(request)
    status = response.status

    if include_kubernetes:
        if os.path.exists(namespace.kubernetes_output):
            os.remove(namespace.kubernetes_output)
        res_json = json.loads(response.data)
        for wf_ps in res_json:
            with open(namespace.kubernetes_output, 'a') as f:
                f.write(res_json[wf_ps]['k8s_specs'])

    if status < 0:
        logging.error(
            f'Error from server: {response.status}, "{response.message}"'
        )
    else:
        if include_kubernetes:
            # Don't spam stderr with the whole yaml dump.
            response_to_print = {}
            for wf_id in res_json:
                response_to_print[wf_id] = {
                    'state': res_json[wf_id]['state']
                }
            logging.info(
                f'Got response: {response.status}, "{response.message}"'
                f', {json.dumps(response_to_print)}'
            )
        else:
            logging.info(
                f'Got response: {response.status}, "{response.message}", {response.data}'
            )
        if namespace.output:
            print(response.data)
    return status
