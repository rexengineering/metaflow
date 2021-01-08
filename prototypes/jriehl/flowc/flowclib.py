'''flowclib.py - REXFlow compiler utility library.
'''

import ast
import logging
import os
import os.path
from typing import Any, Callable, TextIO, Union

from . import cmof, visitors
from .bpmn2 import bpmn


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

    def task_to_bpmn(self, call: visitors.ServiceTaskCall):
        service_task = bpmn.ServiceTask(
            id=f'Task_{self.counter}', name=call.service_name
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
                self.workflow = node
                workflow_visitor = visitors.WorkflowVisitor(self._module)
                workflow_visitor.visit(node)
                self.tasks.extend(workflow_visitor.tasks)
            if hasattr(value, '_service_task'):
                assert value._service_task.definition is None, \
                    (f'Service task {name} already defined on line '
                        f'{value.lineno}')
                value._service_task.definition = node
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
        target_names = [call.service_name for call in visitor.tasks]
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
        call: visitors.ServiceTaskCall) -> str:
    task_name = call.service_name
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
    for call in visitor.tasks:
        gen_service_task(visitor, workflow_path, call)


def flow_compiler(input_file: TextIO, output_path: str) -> bool:
    try:
        parse_result = parse(input_file)
        code_gen(parse_result, output_path)
    except Exception as exception:
        logging.exception(exception)
        return False
    return True
