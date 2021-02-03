import unittest

import graphviz

from .. import flowclib, bpmn_to_dot
from .test_flowclib import HELLO_PATH

class TestBPMNToDot(unittest.TestCase):
    def test_bpmn_to_dot(self):
        with open(HELLO_PATH) as file_obj:
            visitor = flowclib.parse(file_obj)
        definitions = visitor.to_bpmn()
        assert (
            len(definitions) == 1 and
            isinstance(definitions[0], flowclib.bpmn.Process)
        )
        process = definitions[0]
        assert isinstance(process, flowclib.bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        self.assertIsInstance(digraph, graphviz.Digraph)
        digraph_output = str(digraph).split('\n')
        self.assertGreater(len(digraph_output), 2)
        self.assertIn('digraph hello_workflow {', digraph_output)
        self.assertIn('}', digraph_output)


if __name__ == '__main__':
    unittest.main()
