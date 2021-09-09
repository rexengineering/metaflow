#!/usr/bin/env python
'''Insanity checker for the_bugs.bpmn

For who will debug the debugger?
'''
import json
import pprint
from typing import Optional, Sequence

import pudb
import xmltodict
import yaml

from flowctl import cli
from flowlib import bpmn
from flowlib.bpmn_util import BPMN


THE_BUGS = 'the_bugs.bpmn'


def local_validation(spec):
    with open(spec, 'rb') as spec_file_obj:
        xml = xmltodict.parse(spec_file_obj)
    process = None
    if xml is not None:
        process = bpmn.BPMNProcess(xml[BPMN.definitions][BPMN.process])
        if spec == THE_BUGS:
            assure_port_assignments_for_the_bugs(process.to_istio())
    return process


def validate_spec(args:Optional[Sequence[str]]=None) -> dict:
    parser, _ = cli.build_parser_and_action_map()
    namespace = parser.parse_args(args)
    namespace.command = getattr(namespace, 'command', 'validate')
    namespace.bpmn_spec = getattr(namespace, 'bpmn_spec', [THE_BUGS])
    namespace.include_kubernetes = getattr(namespace, 'include_kubernetes', True)
    result = vars(namespace)
    if namespace.command == 'validate':
        grpc_results = cli.validate_action.grpc_validate(namespace)
        assert all(value.status >= 0 for value in grpc_results.values())
        result['results'] = {key: json.loads(value.data) for key, value in grpc_results.items()}
    return result


def assure_port_assignments_for_the_bugs(k8s_source):
    k8s_docs = [doc for doc in yaml.safe_load_all(k8s_source) if doc is not None]
    debuggee_deployments = [doc for doc in k8s_docs if doc['kind'] == 'Deployment' and doc['metadata']['name'] == 'debuggee']
    debuggee_containers = [
        container
        for doc in debuggee_deployments
        for container in doc['spec']['template']['spec']['containers']
        if container['name'] == 'debuggee'
    ]
    assert all(container['ports'][0]['containerPort'] == 5000 for container in debuggee_containers)


def test_the_bugs(*args):
    args_len = len(args)
    if args_len == 0 or args[0] == 'test_local':
        if args_len > 1:
            for spec in args[1:]:
                local_validation(spec)
        else:
            local_validation(THE_BUGS)
    else:
        if args[0] not in cli.ACTIONS:
            args = ['validate', *args]
        results = validate_spec(args).get('results', {})
        for spec, validation_result in results.items():
            if validation_result['status'] < 0:
                print(f'{spec} does not validate.')
                pprint.pprint(validation_result)
            else:
                print(f'{spec} validates.')
                if spec == THE_BUGS:
                    assure_port_assignments_for_the_bugs(validation_result.get('k8s_specs', ''))


if __name__ == '__main__':
    import sys
    test_the_bugs(*sys.argv[1:])
