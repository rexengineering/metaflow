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

DEAD_CODE_SRC_2 = '''
def deader_code():
    if False:
        return universal_law_failure()
        return 42
        pass
    else:
        look_busy()
'''


class TestCFG(unittest.TestCase):
    def test_branch(self):
        with open(BRANCH_PATH) as branch_file:
            toplevel = flowclib.parse(branch_file)
        assert toplevel.workflow is not None
        visitor = cfg.CFGBuilder(toplevel.workflow)
        blocks = visitor.get_cfg()
        self.assertEqual(len(blocks), 4)
        real_block_count = sum(1 for block in blocks if block is not None)
        self.assertEqual(real_block_count, 4)

    @staticmethod
    def _parse(src: str) -> cfg.CFGBuilder:
        tree = ast.parse(src, '<unit test input>', 'exec')
        function_def = tree.body[0]
        assert isinstance(function_def, ast.FunctionDef)
        cfg_visitor = cfg.CFGBuilder(function_def)
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

    def test_deader_code(self):
        cfg_visitor = self._parse(DEAD_CODE_SRC_2)
        cfg_blocks = cfg_visitor.get_cfg()
        block_count = len(cfg_blocks)
        self.assertEqual(block_count, 6)
        real_block_count = sum(1 for block in cfg_blocks if block is not None)
        self.assertLess(real_block_count, block_count)
        self.assertIsNotNone(cfg_blocks[1])
        self.assertEqual(real_block_count, 4)


if __name__ == '__main__':
    unittest.main()
