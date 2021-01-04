import os.path
import shutil
import tempfile
import unittest

from prototypes.jriehl import flowc


PATH = os.path.dirname(__file__)

BRANCH_PATH = os.path.join(PATH, '..', 'branch.py')
HELLO_PATH = os.path.join(PATH, '..', 'hello.py')


class TestFlowC(unittest.TestCase):
    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self._parse_results = {}

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

    def test_codegen(self):
        frontend_result = self._parse_path(HELLO_PATH)
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                flowc.code_gen(frontend_result, temp_path)
                workflow_path = os.path.abspath(
                    os.path.join(temp_path, 'hello_workflow'))
                self.assertTrue(os.path.exists(workflow_path))
            finally:
                shutil.rmtree(temp_path)


if __name__ == '__main__':
    unittest.main()
