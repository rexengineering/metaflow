import unittest

import graphviz

from .. import bpmngen, bpmn_to_dot, flowclib
from ..bpmn2 import bpmn
from .test_flowclib import HELLO_PATH


class TestBPMNToDot(unittest.TestCase):
    def _get_bpmn(self):
        with open(HELLO_PATH) as file_obj:
            visitor = flowclib.parse(file_obj)
        definitions = bpmngen.generate_bpmn(visitor, include_diagram=False)
        assert (
            len(definitions) == 1 and
            isinstance(definitions[0], bpmn.Process)
        )
        return definitions

    def test_bpmn_to_dot(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        self.assertIsInstance(digraph, graphviz.Digraph)
        digraph_output = str(digraph).split('\n')
        self.assertGreater(len(digraph_output), 2)
        self.assertIn('digraph hello_workflow {', digraph_output)
        self.assertIn('}', digraph_output)

    def test_dot_to_xdot(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        xdot = bpmn_to_dot.dot_to_xdot(digraph)
        xdot_output = str(xdot).split('\n')
        self.assertGreater(len(xdot_output), 2)
        self.assertIn('digraph hello_workflow {', xdot_output)
        self.assertIn('}', xdot_output)

    def test_dot_to_svg(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, bpmn.Process)
        digraph = bpmn_to_dot.bpmn_to_dot(process)
        svg = bpmn_to_dot.dot_to_svg(digraph)
        self.assertEqual(len(svg), 1)

    def test_svg_to_bpmndi(self):
        definitions = self._get_bpmn()
        process = definitions[0]
        assert isinstance(process, bpmn.Process)
        process_elements = set(
            getattr(element, 'id', None) for element in process
        )
        diagram = bpmn_to_dot.process_to_diagram(process)
        self.assertIsInstance(diagram, bpmn_to_dot.bpmndi.BPMNDiagram)
        self.assertEqual(len(diagram), 1)
        plane = diagram[0]
        self.assertIsInstance(plane, bpmn_to_dot.bpmndi.BPMNPlane)
        diagram_elements = set(
            getattr(element, 'bpmnElement') for element in plane
        )
        self.assertEqual(process_elements, diagram_elements)

if __name__ == '__main__':
    unittest.main()