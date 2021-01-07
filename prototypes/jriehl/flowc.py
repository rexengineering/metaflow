'''flowc.py - Entry point for REXFlow compiler.
'''

import argparse
import ast
import logging
import os
import os.path
import sys
from typing import Any, Callable, TextIO, Union

from . import cmof
from .bpmn2 import bpmn
from flowlib.flowd_utils import get_log_format


LHSs = Union[
    ast.Attribute,
    ast.Subscript,
    ast.Starred,
    ast.Name,
    ast.List,
    ast.Tuple
]

MAKEFILE_TEMPLATE = '''all: {targets}

test:

clean:

{target_rules}

.PHONY: all {targets} test clean
'''

TARGET_TEMPLATE = '''{target}: {target}/Dockerfile {target}/app.py
\tdocker build -t {target} {target}'''

DOCKERFILE_TEMPLATE = '''FROM python:3-alpine
COPY app.py /
ENTRYPOINT ["python", "/app.py"]
'''

APP_TEMPLATE = '''print('Hello, world.')
'''


class ToplevelVisitor(ast.NodeVisitor):
    def __init__(self, module_dict: dict) -> None:
        self._module = module_dict
        self.tasks = []
        self.workflow = None
        self.bindings = {}
        self.counter = 0
        super().__init__()

    def task_to_bpmn(self, task: ast.FunctionDef):
        service_task = bpmn.ServiceTask(
            id=f'Task_{self.counter}', name=f'{task.name}_{self.counter}'
        )
        self.counter += 1
        return service_task

    def _make_edge(self, source: cmof.Element, target: cmof.Element):
        sequence_flow = bpmn.SequenceFlow(
            id=f'SequenceFlow_{self.counter}',
            sourceRef=source.id,
            targetRef=target.id
        )
        self.counter += 1
        source.append(bpmn.Outgoing(sequence_flow.id))
        target.append(bpmn.Incoming(sequence_flow.id))
        return sequence_flow

    def to_bpmn(self) -> bpmn.Definitions:
        self.counter = 1
        start_event = bpmn.StartEvent(
            id=f'StartEvent_{self.counter}', name='Start'
        )
        self.counter += 1
        # FIXME: Don't forget to change the following to only emit the tasks
        # called in the workflow.
        service_tasks = [self.task_to_bpmn(task) for task in self.tasks]
        end_event = bpmn.EndEvent(id=f'EndEvent_{self.counter}', name='End')
        self.counter += 1
        # FIXME: This is just ridiculous, but true for the current test cases.
        sequence_flows = []
        current = start_event
        for next in service_tasks:
            sequence_flows.append(self._make_edge(current, next))
            current = next
        sequence_flows.append(self._make_edge(current, end_event))
        process = bpmn.Process(id=self.workflow.name, isExecutable=True)
        process.append(start_event)
        process.extend(service_tasks)
        process.append(end_event)
        process.extend(sequence_flows)
        return bpmn.Definitions([process])

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(
            f'Unsupported Python syntax at line {node.lineno}, column '
            f'{node.col_offset} ({type(node).__name__}).'
        )

    def _bind(self, name, value):
        assert name not in self.bindings, f'A name can only be bound once ({name}).'
        self.bindings[name] = value

    def _handle_lhs(self, lhs: LHSs):
        result = None
        if isinstance(lhs, ast.Name):
            assert isinstance(lhs.ctx, ast.Store)
            result = lhs.id
        elif isinstance(lhs, ast.Starred):
            result = self._handle_lhs(lhs.value)
        elif isinstance(lhs, (ast.List, ast.Tuple)):
            container_type = list if isinstance(lhs, ast.List) else tuple
            result = container_type(self._handle_lhs(elt) for elt in lhs.elts)
        return result

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            name_or_names = self._handle_lhs(target)
            if isinstance(name_or_names, str):
                self._bind(name_or_names, node)
            else:
                for name in name_or_names:
                    self._bind(name, node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        name = node.name
        value = self._module.get(name)
        if value:
            if hasattr(value, '_workflow'):
                assert self.workflow is None, \
                    'Only one workflow may be defined in a module.'
                node = WorkflowTransformer(self).visit(node)
                node = ast.fix_missing_locations(node)
                self.workflow = node
                code_obj = compile(
                    ast.Module([node], []),
                    self._module.get('__file__'),
                    'exec'
                )
                exec(code_obj, self._module)
            if hasattr(value, '_service_task'):
                self.tasks.append(node)
        self._bind(node.name, node)

    def _handle_import(self, node: Union[ast.Import, ast.ImportFrom]) -> Any:
        for alias in node.names:
            if alias.asname:
                self._bind(alias.asname, node)
            else:
                self._bind(alias.name, node)

    def visit_Import(self, node: ast.Import) -> Any:
        return self._handle_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        return self._handle_import(node)

    def visit_Module(self, node: ast.Module) -> Any:
        result = super().generic_visit(node)
        assert self.workflow is not None, 'Failed to find a workflow.'
        return result


class WorkflowTransformer(ast.NodeTransformer):
    def __init__(self, visitor: ToplevelVisitor) -> None:
        self.visitor = visitor
        super().__init__()

    def visit_arguments(self, node: ast.arguments) -> Any:
        valid = all((
            (len(node.posonlyargs) == 0),
            (len(node.args) == 0),
            (len(node.kwonlyargs) == 0),
            (not node.vararg),
            (not node.kwarg)
        ))
        assert valid, 'Workflow functions should have no arguments.'
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        node.args.args.append(ast.arg(arg='__wf_env', annotation=None, type_comment=None))
        node.body = [self.generic_visit(child) for child in node.body]
        node.body.append(ast.Return(value=ast.Name(id='__wf_env', ctx=ast.Load())))
        return node

    def visit_Name(self, node: ast.Name) -> Any:
        # The following conditional is an approximation to the rule that
        # the environment consists of literals, while functions (and technically
        # classes) need to remain as they are so they are picked up by the
        # freezing process.
        if ((node.id not in self.visitor._module)
                or (not isinstance(self.visitor._module[node.id], Callable))):
            node = ast.Subscript(
                value=ast.Name(id='__wf_env', ctx=ast.Load()),
                slice=ast.Index(value=ast.Constant(value=node.id)),
                ctx=node.ctx
            )
        return node

    def visit_Return(self, node: ast.Return) -> Any:
        if not node.value:
            node.value = ast.Name(id='__wf_env', ctx=ast.Load())
        else:
            node = super().generic_visit(node)
        return node


def parse(file_obj: TextIO) -> ToplevelVisitor:
    '''Parse an input file object.
    '''
    file_path = os.path.abspath(file_obj.name)
    source = file_obj.read()
    tree = ast.parse(source, file_path, type_comments=True)
    code_obj = compile(tree, file_path, 'exec')
    module_dict = {
        '__file__': file_path,
        '__name__': os.path.splitext(os.path.basename(file_path))[0],
    }
    exec(code_obj, module_dict)
    visitor = ToplevelVisitor(module_dict)
    visitor.visit(tree)
    return visitor


def gen_workflow(visitor: ToplevelVisitor, output_path: str) -> str:
    workflow_name = visitor.workflow.name
    workflow_path = os.path.join(output_path, workflow_name)
    os.mkdir(workflow_path)
    bpmn = visitor.to_bpmn()  # type: cmof.Element
    bpmn_path = os.path.join(workflow_path, f'{workflow_name}.bpmn')
    with open(bpmn_path, 'w') as bpmn_file:
        bpmn_file.write(bpmn.to_xml(pretty=True, short_empty_elements=True))
    makefile_path = os.path.join(workflow_path, 'Makefile')
    with open(makefile_path, 'w') as makefile_file:
        target_names = [task.name for task in visitor.tasks]
        targets = ' '.join(target_names)
        target_rules = '\n\n'.join(TARGET_TEMPLATE.format(
            target=target) for target in target_names
        )
        makefile_file.write(
            MAKEFILE_TEMPLATE.format(
                targets=targets, target_rules=target_rules)
        )
    return workflow_path


def gen_service_task(
        visitor: ToplevelVisitor,
        output_path: str,
        task: ast.FunctionDef) -> str:
    task_name = task.name
    task_path = os.path.join(output_path, task_name)
    os.mkdir(task_path)
    dockerfile_path = os.path.join(task_path, 'Dockerfile')
    with open(dockerfile_path, 'w') as dockerfile_file:
        dockerfile_file.write(DOCKERFILE_TEMPLATE)
    app_path = os.path.join(task_path, 'app.py')
    with open(app_path, 'w') as app_file:
        app_file.write(APP_TEMPLATE)
    return task_path


def code_gen(visitor: ToplevelVisitor, output_path: str):
    output_dir = os.path.abspath(output_path)
    assert os.path.exists(output_dir), f'{output_dir} does not exist'
    workflow_path = gen_workflow(visitor, output_dir)
    for task in visitor.tasks:
        gen_service_task(visitor, workflow_path, task)


def flow_compiler(input_file: TextIO, output_path: str) -> bool:
    try:
        parse_result = parse(input_file)
        code_gen(parse_result, output_path)
    except Exception as exception:
        logging.exception(exception)
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='flowc')
    parser.add_argument(
        'sources', metavar='source', nargs='*', type=open,
        help='input source file(s)'
    )
    parser.add_argument(
        '--log_level', nargs=1, default=logging.INFO, type=int,
        help=f'logging level (DEBUG={logging.DEBUG}, INFO={logging.INFO}...)'
    )
    parser.add_argument(
        '-o', '--output_path', nargs=1, default='.', type=str,
        help='target output path (defaults to .)'
    )
    namespace = parser.parse_args()
    logging.basicConfig(
        format=get_log_format('flowc'), level=namespace.log_level
    )
    if len(namespace.sources) == 0:
        if not flow_compiler(sys.stdin, namespace.output_path):
            sys.exit(1)
    else:
        if not all(
            flow_compiler(source, namespace.output_path)
            for source in namespace.sources
        ):
            sys.exit(1)
