import os.path
import shutil
import tempfile
import unittest

import xmltodict

from prototypes.jriehl import flowc


PATH = os.path.dirname(__file__)

BRANCH_PATH = os.path.join(PATH, '..', 'branch.py')
HELLO_PATH = os.path.join(PATH, '..', 'hello.py')


class TestFlowC(unittest.TestCase):
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
            result = flowc.parse(file_obj)
        self._parse_results[file_path] = result
        return result

    def test_parse_hello(self):
        result = self._parse_path(HELLO_PATH)
        self.assertIsInstance(result, flowc.ToplevelVisitor)

    def test_parse_branch(self):
        result = self._parse_path(BRANCH_PATH)
        self.assertIsInstance(result, flowc.ToplevelVisitor)

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

    def _check_task(self, task_path: str):
        self.assertTrue(
            os.path.isdir(task_path),
            f'{task_path} does not exist or is not a directory'
        )
        dockerfile_path = os.path.join(task_path, 'Dockerfile')
        self.assertTrue(
            os.path.exists(dockerfile_path), f'{dockerfile_path} does not exist'
        )
        app_path = os.path.join(task_path, 'app.py')
        self.assertTrue(
            os.path.exists(app_path), f'{app_path} does not exist'
        )

    def test_codegen(self):
        frontend_result = self._parse_path(HELLO_PATH)
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                flowc.code_gen(frontend_result, temp_path)
                workflow_path = os.path.abspath(
                    os.path.join(temp_path, 'hello_workflow'))
                self.assertTrue(os.path.exists(workflow_path))
                bpmn_path = os.path.join(workflow_path, 'hello_workflow.bpmn')
                self._check_bpmn(bpmn_path)
                makefile_path = os.path.join(workflow_path, 'Makefile')
                self._check_makefile(makefile_path)
                task_path = os.path.join(workflow_path, 'hello_task')
                self._check_task(task_path)
            finally:
                shutil.rmtree(temp_path)


if __name__ == '__main__':
    unittest.main()
