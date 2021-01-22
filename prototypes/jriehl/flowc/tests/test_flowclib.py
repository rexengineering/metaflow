import ast
import os
import os.path
import shutil
import tempfile
from typing import List, Tuple
import unittest

import xmltodict

from .. import flowclib


PATH = os.path.dirname(__file__)
EXAMPLE_PATH = os.path.abspath(os.path.join(PATH, '..', 'examples'))

BRANCH_PATH = os.path.join(EXAMPLE_PATH, 'branch.py')
HELLO_PATH = os.path.join(EXAMPLE_PATH, 'hello.py')
HELLO2_PATH = os.path.join(EXAMPLE_PATH, 'hello2.py')
HELLO3_PATH = os.path.join(EXAMPLE_PATH, 'hello3.py')
ARGS_PATH = os.path.join(EXAMPLE_PATH, 'args.py')


def _has_docker():
    import docker
    import docker.errors
    try:
        docker.from_env()
    except docker.errors.DockerException:
        return False
    return True


class TestFlowCLib(unittest.TestCase):
    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self._parse_results = {}

    def assertNotEmpty(self, container):
        if not container:
            self.fail('Empty or non-existant container')
        self.assertGreaterEqual(len(container), 1)

    def _parse_path(self, file_path):
        if file_path in self._parse_results:
            return self._parse_results[file_path]
        with open(file_path) as file_obj:
            result = flowclib.parse(file_obj)
        self._parse_results[file_path] = result
        return result

    def test_parse_hello(self):
        result = self._parse_path(HELLO_PATH)
        self.assertIsInstance(result, flowclib.ToplevelVisitor)

    def test_parse_branch(self):
        result = self._parse_path(BRANCH_PATH)
        self.assertIsInstance(result, flowclib.ToplevelVisitor)

    def _check_bpmn(self, bpmn_path: str):
        self.assertTrue(
            os.path.exists(bpmn_path), f'{bpmn_path} does not exist'
        )
        with open(bpmn_path, 'rb') as bpmn_file:
            bpmn_dict = xmltodict.parse(bpmn_file, 'utf-8')
        self.assertTrue(
            'bpmn:definitions' in bpmn_dict,
            f'Root element in {bpmn_path} is not a BPMN Definitions '
            'instance'
        )
        definitions_dict = bpmn_dict['bpmn:definitions']
        self.assertNotEmpty(definitions_dict)
        self.assertIn('bpmn:process', definitions_dict)
        process_dict = definitions_dict['bpmn:process']
        self.assertNotEmpty(process_dict)
        self.assertIn('bpmn:startEvent', process_dict)
        self.assertIn('bpmn:serviceTask', process_dict)
        self.assertIn('bpmn:endEvent', process_dict)
        self.assertIn('bpmn:sequenceFlow', process_dict)

    def _check_makefile(self, makefile_path: str):
        self.assertTrue(
            os.path.exists(makefile_path), f'{makefile_path} does not exist'
        )
        with open(makefile_path) as makefile_file:
            makefile_src = makefile_file.read()
        self.assertRegex(makefile_src, r'all\w*:')
        self.assertRegex(makefile_src, r'clean\w*:')
        self.assertRegex(makefile_src, r'test\w*:')
        self.assertRegex(makefile_src, r'.PHONY\w*:')

    def _check_function(
            self,
            function_definition: ast.FunctionDef,
            expected_assigns: str) -> str:
        expected_module = ast.parse(expected_assigns, mode='exec')
        assert isinstance(expected_module, ast.Module)
        assert len(expected_module.body) > 0
        expected_body = expected_module.body
        assert all(
            isinstance(expected_assign_tree, ast.Assign)
            for expected_assign_tree in expected_body
        )
        expected_body.append(
            ast.Return(value=ast.Name(id='environment', ctx=ast.Load()))
        )
        expected = ast.dump(
            ast.FunctionDef(
                name=function_definition.name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(
                        arg='environment', annotation=None, type_comment=None
                    )],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[]
                ),
                body=expected_body,
                decorator_list=[],
                returns=None,
                type_comment=None
            )
        )
        actual = ast.dump(function_definition)
        self.assertEqual(actual, expected)
        return function_definition.name

    def _check_task_app(
            self, task_name: str, app_source: str, wrapped_body: str):
        app_tree = ast.parse(app_source, 'app.py', 'exec')
        self.assertNotEmpty(app_tree.body)
        function_definitions = [
            stmt for stmt in app_tree.body if isinstance(stmt, ast.FunctionDef)
        ]
        self.assertNotEmpty(function_definitions)
        function_map = {
            function_definition.name: function_definition
            for function_definition in function_definitions
        }
        self.assertIn(task_name, function_map)
        target = self._check_function(function_map[task_name], wrapped_body)
        self.assertIn(target, function_map)

    def _check_wrapped_function_noargs(
            self,
            function_definition: ast.FunctionDef,
            assign_targets: str) -> str:
        target = function_definition.name.rsplit('_', 1)[0]
        self._check_function(
            function_definition, f'{assign_targets} = {target}()'
        )
        return target

    def _check_task(self, out_path: str, task_name: str, assign_targets: str):
        task_path = os.path.join(out_path, task_name)
        self.assertTrue(
            os.path.isdir(task_path),
            f'{task_path} does not exist or is not a directory'
        )
        dockerfile_path = os.path.join(task_path, 'Dockerfile')
        self.assertTrue(
            os.path.exists(dockerfile_path), f'{dockerfile_path} does not exist'
        )
        with open(dockerfile_path) as dockerfile_file:
            dockerfile_src = dockerfile_file.read()
        self.assertIn('FROM', dockerfile_src)
        self.assertIn('COPY', dockerfile_src)
        self.assertIn('ENTRYPOINT', dockerfile_src)
        app_path = os.path.join(task_path, 'app.py')
        self.assertTrue(
            os.path.exists(app_path), f'{app_path} does not exist'
        )
        with open(app_path) as app_file:
            app_src = app_file.read()
        app_tree = ast.parse(app_src, app_path)
        self.assertNotEmpty(app_tree.body)
        function_definitions = [
            stmt for stmt in app_tree.body if isinstance(stmt, ast.FunctionDef)
        ]
        self.assertNotEmpty(function_definitions)
        function_map = {
            function_definition.name: function_definition
            for function_definition in function_definitions
        }
        self.assertIn(task_name, function_map)
        target = self._check_wrapped_function_noargs(
            function_map[task_name], assign_targets
        )
        self.assertIn(target, function_map)

    def _check_codegen(
            self,
            source_path: str,
            workflow_name: str,
            task_data: List[Tuple[str, str]]):
        frontend_result = self._parse_path(source_path)
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                flowclib.code_gen(frontend_result, temp_path)
                workflow_path = os.path.abspath(
                    os.path.join(temp_path, workflow_name))
                self.assertTrue(os.path.exists(workflow_path))
                bpmn_path = os.path.join(workflow_path, f'{workflow_name}.bpmn')
                self._check_bpmn(bpmn_path)
                makefile_path = os.path.join(workflow_path, 'Makefile')
                self._check_makefile(makefile_path)
                for task_name, task_assigns in task_data:
                    self._check_task(workflow_path, task_name, task_assigns)
            finally:
                shutil.rmtree(temp_path)

    def test_codegen(self):
        self._check_codegen(HELLO_PATH, 'hello_workflow', [
            ('hello_task_1', 'environment[\'result\']'),
        ])

    def test_multiassign(self):
        self._check_codegen(HELLO2_PATH, 'hello2_workflow', [
            ('hello2_task_1', 'environment[\'hello\'], environment[\'world\']'),
        ])

    def test_noassign(self):
        self._check_codegen(HELLO3_PATH, 'hello3_workflow', [
            ('hello3_task_1', 'environment[\'$result\']')
        ])

    def test_args(self):
        with open(ARGS_PATH) as file_obj:
            parse_result = flowclib.parse(file_obj)
        self.assertNotEmpty(parse_result.tasks)
        expected_args = (
            "'test subject'",
            "environment['result0']",
            "name='Joe Bob'",
            "name=environment['result2']",
        )
        for call, args in zip(parse_result.tasks, expected_args):
            app_source = flowclib.gen_service_task_app(parse_result, call)
            self._check_task_app(
                f'hello_arg_task_{call.index}',
                app_source,
                f"environment['result{call.index - 1}'] = hello_arg_task("
                    f'{args})'
            )

    @unittest.skipUnless(_has_docker(), 'Docker not present, skipping...')
    def test_make(self):
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                with open(HELLO_PATH) as hello_file:
                    flowc_ok = flowclib.flow_compiler(hello_file, temp_path)
                    self.assertTrue(
                        flowc_ok, 'Flow compiler failed to handle hello.py!'
                    )
                workflow_path = os.path.join(temp_path, 'hello_workflow')
                result = os.system(f'make -C {workflow_path}')
                self.assertEqual(
                    result, 0, f'Make failed with exit code {result}'
                )
            finally:
                shutil.rmtree(temp_path)

    def test_fail(self):
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                test_path = os.path.join(PATH, '..', '__main__.py')
                with open(test_path) as test_file, \
                        self.assertLogs() as logging_manager:
                    flowc_ok = flowclib.flow_compiler(test_file, temp_path)
                self.assertFalse(
                    flowc_ok,
                    'Flow compiler failed to signal a problem with invalid '
                    'input.'
                )
                self.assertNotEmpty(logging_manager.output)
                self.assertNotIn(
                    '"\'__name__\' not in globals"', logging_manager.output[0]
                )
            finally:
                shutil.rmtree(temp_path)


if __name__ == '__main__':
    unittest.main()
