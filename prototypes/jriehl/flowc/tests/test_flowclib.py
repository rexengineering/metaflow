import ast
import os
import os.path
import shutil
import tempfile
import unittest

import xmltodict

from .. import flowclib


PATH = os.path.dirname(__file__)
EXAMPLE_PATH = os.path.abspath(os.path.join(PATH, '..', 'examples'))

BRANCH_PATH = os.path.join(EXAMPLE_PATH, 'branch.py')
HELLO_PATH = os.path.join(EXAMPLE_PATH, 'hello.py')


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

    def _check_task(self, out_path: str, task_name: str):
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
        self.assertIn(task_name.rsplit('_', 1)[0], function_map)

    def test_codegen(self):
        frontend_result = self._parse_path(HELLO_PATH)
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                flowclib.code_gen(frontend_result, temp_path)
                workflow_path = os.path.abspath(
                    os.path.join(temp_path, 'hello_workflow'))
                self.assertTrue(os.path.exists(workflow_path))
                bpmn_path = os.path.join(workflow_path, 'hello_workflow.bpmn')
                self._check_bpmn(bpmn_path)
                makefile_path = os.path.join(workflow_path, 'Makefile')
                self._check_makefile(makefile_path)
                self._check_task(workflow_path, 'hello_task_1')
            finally:
                shutil.rmtree(temp_path)

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
