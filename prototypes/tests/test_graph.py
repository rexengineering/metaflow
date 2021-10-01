import unittest

from .. import graphplay

class TestDigraph(unittest.TestCase):
    def test_digraph(self):
        graph = graphplay.Digraph()
        vertex = graphplay.Vertex(graph)
        vertex._ignored_edge = 128
        self.assertTrue('_ignored_edge' not in graph.map[vertex])
        self.assertEqual(vertex._ignored_edge, 128)
        other = graphplay.Vertex(graph)
        vertex.edge = other
        self.assertEqual(graph.map[vertex]['edge'], vertex.edge)

    def test_vertex_inheritance(self):
        graph = graphplay.Digraph()
        other = graphplay.Vertex(graph)

        class MyVertex(graphplay.Vertex):
            def __init__(self, graph: graphplay.Digraph):
                super().__init__(graph)
                self.edge = other
                self._ignored_edge = 256

        vertex = MyVertex(graph)
        self.assertTrue('_ignored_edge' not in graph.map[vertex])
        self.assertEqual(vertex._ignored_edge, 256)
        self.assertEqual(graph.map[vertex]['edge'], vertex.edge)

class TestDigraph2(unittest.TestCase):
    class MyVertex:
        pass

    def test_digraph2(self):
        graph = graphplay.Digraph2()
        vertex = graph.wrap(self.MyVertex())
        vertex._ignored_edge = 512
        self.assertTrue('_ignored_edge' not in graph.map[vertex])
        self.assertEqual(vertex._ignored_edge, 512)
        other = graph.wrap(self.MyVertex())
        vertex.edge = other
        self.assertEqual(graph.map[vertex]['edge'], vertex.edge)

if __name__ == '__main__':
    unittest.main()
