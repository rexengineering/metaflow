'''flowclib.py - REXFlow compiler utility library.
'''

import ast
import logging
import os
import os.path
import shutil
from typing import TextIO

import jinja2

from . import bpmngen, cmof, flowcode, quart_wrapper, toplevel, visitors


MAKEFILE_TEMPLATE = '''all: {targets}

test:

clean:

{target_rules}

.PHONY: all {targets} test clean
'''

TARGET_TEMPLATE = '''{target}: {target}/Dockerfile {target}/app.py
\tdocker build -t {target} {target}'''

DOCKERFILE_TEMPLATE = '''FROM python:3-alpine
COPY requirements.txt *.py /opt/wf/
RUN pip install -r /opt/wf/requirements.txt
ENV PYTHONPATH=/opt/wf
EXPOSE 8000
ENTRYPOINT ["hypercorn", "-b", "0.0.0.0", "app:app"]
'''

SERVICE_TASK_FUNCTION_TEMPLATE = '''def {function_name}(environment):
    {assign_targets} = {call_target_name}({args})
    return environment
'''

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.PackageLoader('prototypes.jriehl.flowc', '.'),
    autoescape=jinja2.select_autoescape(['.py']),
)

APP_TEMPLATE = JINJA_ENVIRONMENT.get_template('app.py.jinja2')
REQUIREMENTS_TEMPLATE = JINJA_ENVIRONMENT.get_template(
    'requirements.txt.jinja2'
)


def _unparse(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        slice = node.slice
        if isinstance(slice, ast.Index):
            return f'{_unparse(node.value)}[{_unparse(slice.value)}]'
        raise NotImplementedError(
            f'Unhandled subscript target at line {slice.lineno} '
            f'({ast.dump(slice)})'
        )
    elif isinstance(node, ast.Tuple):
        return ', '.join(_unparse(elt) for elt in node.elts)
    raise NotImplementedError(
        f'Unhandled assignment target at line {node.lineno} '
        f'({ast.dump(node)})'
    )


def unparse(node: ast.expr) -> str:
    if hasattr(ast, 'unparse'):
        python_unparse = getattr(ast, 'unparse')
        result = python_unparse(node)
    else:
        result = _unparse(node)
    return result


def parse(file_obj: TextIO) -> toplevel.ToplevelVisitor:
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
    visitor = toplevel.ToplevelVisitor(source, module_dict)
    visitor.visit(tree)
    return visitor


def gen_workflow(visitor: toplevel.ToplevelVisitor, output_path: str) -> str:
    workflow_name = visitor.workflow.name
    workflow_path = os.path.join(output_path, workflow_name)
    os.mkdir(workflow_path)
    bpmn = bpmngen.generate_bpmn(visitor)  # type: cmof.Element
    bpmn_path = os.path.join(workflow_path, f'{workflow_name}.bpmn')
    with open(bpmn_path, 'w') as bpmn_file:
        bpmn.to_xml(output=bpmn_file, pretty=True, short_empty_elements=True)
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


def gen_service_task_app(
        visitor: toplevel.ToplevelVisitor,
        call: visitors.ServiceTaskCall) -> str:
    task_function = visitor.get_module_value(call.task_name)
    assert hasattr(task_function, '_service_task') and \
        isinstance(task_function._service_task, flowcode.ServiceTask)
    task_definition = task_function._service_task.definition
    wrapper_name = f'{call.task_name}_{call.index}'
    args = ', '.join(unparse(arg) for arg in call.args)
    if len(call.keywords) > 0:
        if len(args) > 0:
            args += ', '
        args += ', '.join(
            f'{keyword.arg}={unparse(keyword.value)}'
            for keyword in call.keywords
        )
    wrapper_source = SERVICE_TASK_FUNCTION_TEMPLATE.format(
        function_name=wrapper_name,
        assign_targets=(
            'environment[\'$result\']'
            if call.targets is None else
            ', '.join(unparse(target) for target in call.targets)
        ),
        call_target_name=call.task_name,
        args=args
    )
    return APP_TEMPLATE.render(
        dependencies=[
            visitor.get_source(
                task_definition.lineno, task_definition.col_offset,
                task_definition.end_lineno, task_definition.end_col_offset,
            ),
        ],
        service_task_function=wrapper_source,
        service_task_function_name=wrapper_name,
    )


def gen_service_task(
        visitor: toplevel.ToplevelVisitor,
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
        app_file.write(gen_service_task_app(visitor, call))
    target_path = os.path.join(task_path, 'quart_wrapper.py')
    shutil.copyfile(quart_wrapper.__file__, target_path)
    requirements_path = os.path.join(task_path, 'requirements.txt')
    with open(requirements_path, 'w') as requirements_file:
        requirements_file.write(REQUIREMENTS_TEMPLATE.render(
            dependencies=[],
        ))
    return task_path


def code_gen(visitor: toplevel.ToplevelVisitor, output_path: str):
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
