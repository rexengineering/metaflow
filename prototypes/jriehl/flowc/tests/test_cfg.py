import unittest

from .. import cfg, flowclib
from .test_flowclib import BRANCH_PATH


class TestCFG(unittest.TestCase):
    def test_branch(self):
        with open(BRANCH_PATH) as branch_file:
            toplevel = flowclib.parse(branch_file)
        assert toplevel.workflow is not None
        visitor = cfg.CFGTransfomer(toplevel.workflow)
        blocks = visitor.get_cfg()
        self.assertEqual(len(blocks), 4)


if __name__ == '__main__':
    unittest.main()
