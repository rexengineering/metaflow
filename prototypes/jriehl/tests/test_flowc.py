import os.path
import unittest

from prototypes.jriehl import flowc


PATH = os.path.dirname(__file__)

BRANCH_PATH = os.path.join(PATH, '..', 'branch.py')
HELLO_PATH = os.path.join(PATH, '..', 'hello.py')


class TestFlowC(unittest.TestCase):
    def _parse_and_test_path(self, file_path):
        with open(file_path) as file_obj:
            self.assertIsInstance(flowc.parse(file_obj), flowc.ToplevelVisitor)

    def test_parse_hello(self):
        self._parse_and_test_path(HELLO_PATH)

    def test_parse_branch(self):
        self._parse_and_test_path(BRANCH_PATH)


if __name__ == '__main__':
    unittest.main()
