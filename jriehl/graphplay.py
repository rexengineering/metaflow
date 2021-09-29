from typing import Any, Optional, Sequence
import weakref

class Digraph:
    def __init__(self):
        self.map = {}

class Vertex:
    def __init__(self, graph: Digraph):
        self._graph = weakref.ref(graph)
        graph.map[self] = {}

    def __setattr__(self, name: str, value: Any) -> None:
        if not name.startswith('_'):
            graph = self._graph()
            graph.map[self][name] = value
        super().__setattr__(name, value)

class Digraph2:
    def __init__(self):
        self.map = {}

    def wrap(self, vertex: object):
        class VertexWrapper(type(vertex)):
            def __init__(instance):
                self.map[instance] = {}

            def __getattr__(self, name: str) -> Any:
                return getattr(vertex, name)

            def __setattr__(inst, name: str, value: Any) -> None:
                if not name.startswith('_'):
                    self.map[inst][name] = value
                return vertex.__setattr__(name, value)

            @property
            def wrapped(self):
                return vertex

        result = VertexWrapper()
        return result

class ControlFlowGraph(Digraph):
    def __init__(self, describes = None):
        self._describes(describes)
        super().__init__()

class BasicBlock(Vertex):
    def __init__(self, graph: ControlFlowGraph):
        self._statements = [] # type: Sequence
        self._conditional = None
        self.true_branch = None # type: Optional[BasicBlock]
        self.false_branch = None # type: Optional[BasicBlock]
        self._terminal = False # type: bool
        super().__init__(graph)

