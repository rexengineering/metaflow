import ast
import unittest

from .. import cfg, flowclib
from .test_flowclib import BRANCH_PATH


NO_ORELSE_SRC = '''
def no_orelse():
    if some_predicate():
        do_something()
'''

DEAD_CODE_SRC = '''
def dead_code():
    return 42
    pass
'''

class TestCFG(unittest.TestCase):
    def test_branch(self):
        with open(BRANCH_PATH) as branch_file:
            toplevel = flowclib.parse(branch_file)
        assert toplevel.workflow is not None
        visitor = cfg.CFGTransfomer(toplevel.workflow)
        blocks = visitor.get_cfg()
        self.assertEqual(len(blocks), 4)

    @staticmethod
    def _parse(src: str) -> cfg.CFGTransfomer:
        tree = ast.parse(src, '<unit test input>', 'exec')
        function_def = tree.body[0]
        assert isinstance(function_def, ast.FunctionDef)
        cfg_visitor = cfg.CFGTransfomer(function_def)
        return cfg_visitor

    def test_empty(self):
        cfg_visitor = self._parse(NO_ORELSE_SRC)
        cfg_blocks = cfg_visitor.get_cfg()
        self.assertEqual(len(cfg_blocks), 3)
        self.assertIsNotNone(cfg_blocks[-1].terminal)

    def test_dead_code(self):
        cfg_visitor = self._parse(DEAD_CODE_SRC)
        cfg_blocks = cfg_visitor.get_cfg()
        self.assertEqual(len(cfg_blocks), 1)
        self.assertIsNotNone(cfg_blocks[-1].terminal)


if __name__ == '__main__':
    unittest.main()
