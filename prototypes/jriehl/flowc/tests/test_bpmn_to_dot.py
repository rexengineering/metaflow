import unittest

import graphviz

from .. import flowclib, bpmn_to_dot
from .test_flowclib import HELLO_PATH

class TestBPMNToDot(unittest.TestCase):
    def _get_bpmn(self):
        with open(HELLO_PATH) as file_obj:
            visitor = flowclib.parse(file_obj)
        definitions = visitor.to_bpmn()
        assert (
            len(definitions) == 1 and
            isinstance(definitions[0], flowclib.bpmn.Process)
        )
        return definitions

    def test_bpmn_to_dot(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, flowclib.bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        self.assertIsInstance(digraph, graphviz.Digraph)
        digraph_output = str(digraph).split('\n')
        self.assertGreater(len(digraph_output), 2)
        self.assertIn('digraph hello_workflow {', digraph_output)
        self.assertIn('}', digraph_output)

    def test_dot_to_xdot(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, flowclib.bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        xdot = bpmn_to_dot.dot_to_xdot(digraph)
        xdot_output = str(xdot).split('\n')
        self.assertGreater(len(xdot_output), 2)
        self.assertIn('digraph hello_workflow {', xdot_output)
        self.assertIn('}', xdot_output)

    def test_dot_to_svg(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, flowclib.bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        svg = bpmn_to_dot.dot_to_svg(digraph)
        self.assertEqual(len(svg), 1)

if __name__ == '__main__':
    unittest.main()
