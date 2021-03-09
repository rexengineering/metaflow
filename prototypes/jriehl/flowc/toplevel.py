import ast
from typing import Any, Dict, List, Optional, Union

from . import cfg, visitors
from .bpmn2 import bpmn


LHSs = Union[
    ast.Attribute,
    ast.Subscript,
    ast.Starred,
    ast.Name,
    ast.List,
    ast.Tuple
]


class ToplevelVisitor(ast.NodeVisitor):
    def __init__(
            self,
            module_source: str,
            module_dict: dict,
            newline: str = '\n') -> None:
        self._newline = newline
        self._module_source = module_source.split(self._newline)
        self._module: Dict[str, Any] = module_dict
        self.tasks: List[visitors.ServiceTaskCall] = []
        self.workflow: Optional[ast.FunctionDef] = None
        self.bindings: Dict[str, ast.AST] = {}
        self.blocks: cfg.CFGBlocks = []
        super().__init__()

    def get_module_keys(self):
        return self._module.keys()

    def get_module_value(self, key):
        return self._module[key]

    def get_source(self, start_line=1, start_column=0, end_line=None,
                   end_column=-1):
        if end_line is None:
            end_line = len(self._module_source)
        source_lines = [
            line[:] for line in self._module_source[start_line - 1:end_line]
        ]
        if len(source_lines) == 1:
            if end_column < 0:
                return source_lines[0][start_column:] + self._newline
            return source_lines[0][start_column:end_column]
        elif len(source_lines) > 1:
            source_lines[0] = source_lines[0][start_column:]
            source_lines[-1] = source_lines[-1][:end_column]
            return self._newline.join(source_lines)
        return ''

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(
            f'Unsupported Python syntax at line {node.lineno}, column '
            f'{node.col_offset} ({type(node).__name__}).'
        )

    def _bind(self, name: str, value: ast.AST) -> None:
        assert name not in self.bindings, f'A name can only be bound once ({name}).'
        self.bindings[name] = value

    def _cast_lhs(self, expression: ast.expr) -> LHSs:
        assert isinstance(expression, LHSs), 'Unsupported left-hand ' \
            f'subexpression found in assignment ({type(expression)}).'
        return expression

    def _handle_lhs(self, lhs: LHSs):
        result = None
        if isinstance(lhs, ast.Name):
            assert isinstance(lhs.ctx, ast.Store)
            result = lhs.id
        elif isinstance(lhs, ast.Starred):
            result = self._handle_lhs(self._cast_lhs(lhs.value))
        elif isinstance(lhs, (ast.List, ast.Tuple)):
            container_type = list if isinstance(lhs, ast.List) else tuple
            result = container_type(
                self._handle_lhs(self._cast_lhs(elt)) for elt in lhs.elts
            )
        return result

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            name_or_names = self._handle_lhs(self._cast_lhs(target))
            if isinstance(name_or_names, str):
                self._bind(name_or_names, node)
            else:
                for name in name_or_names:
                    self._bind(name, node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        name = node.name
        value = self._module.get(name)
        if value:
            if hasattr(value, '_workflow'):
                assert self.workflow is None, \
                    'Only one workflow may be defined in a module.'
                self.workflow = node
                workflow_visitor = visitors.WorkflowVisitor(self._module)
                workflow_visitor.visit(node)
                self.tasks.extend(workflow_visitor.tasks)
                builder = cfg.CFGBuilder(node)
                self.blocks = builder.get_cfg()
            if hasattr(value, '_service_task'):
                assert value._service_task.definition is None, \
                    (f'Service task {name} already defined on line '
                        f'{value.lineno}')
                value._service_task.definition = node
        self._bind(name, node)

    def _handle_import(self, node: Union[ast.Import, ast.ImportFrom]) -> Any:
        for alias in node.names:
            if alias.asname:
                self._bind(alias.asname, node)
            else:
                self._bind(alias.name, node)

    def visit_Import(self, node: ast.Import) -> Any:
        return self._handle_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        return self._handle_import(node)

    def visit_Module(self, node: ast.Module) -> Any:
        result = super().generic_visit(node)
        assert self.workflow is not None, 'Failed to find a workflow.'
        return result
