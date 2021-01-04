'''flowc.py - Entry point for REXFlow compiler.
'''

import argparse
import ast
import logging
import os.path
import sys
from typing import Any, Callable, TextIO, Union

from flowlib.flowd_utils import get_log_format


LHSs = Union[
    ast.Attribute,
    ast.Subscript,
    ast.Starred,
    ast.Name,
    ast.List,
    ast.Tuple
]


class ToplevelVisitor(ast.NodeVisitor):
    def __init__(self, module_dict: dict) -> None:
        self._module = module_dict
        self.tasks = []
        self.workflow = None
        self.bindings = {}
        super().__init__()

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(
            f'Unsupported Python syntax at line {node.lineno}, column {node.col_offset} ({type(node).__name__}).'
        )

    def _bind(self, name, value):
        assert name not in self.bindings, f'A name can only be bound once ({name}).'
        self.bindings[name] = value

    def _handle_lhs(self, lhs: LHSs):
        result = None
        if isinstance(lhs, ast.Name):
            assert isinstance(lhs.ctx, ast.Store)
            result = lhs.id
        elif isinstance(lhs, ast.Starred):
            result = self._handle_lhs(lhs.value)
        elif isinstance(lhs, (ast.List, ast.Tuple)):
            container_type = list if isinstance(lhs, ast.List) else tuple
            result = container_type(self._handle_lhs(elt) for elt in lhs.elts)
        return result

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            name_or_names = self._handle_lhs(target)
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
                node = WorkflowTransformer(self).visit(node)
                node = ast.fix_missing_locations(node)
                self.workflow = node
                code_obj = compile(
                    ast.Module([node], []),
                    self._module.get('__file__'),
                    'exec'
                )
                exec(code_obj, self._module)
            if hasattr(value, '_service_task'):
                self.tasks.append(node)
        self._bind(node.name, node)

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


class WorkflowTransformer(ast.NodeTransformer):
    def __init__(self, visitor: ToplevelVisitor) -> None:
        self.visitor = visitor
        super().__init__()

    def visit_arguments(self, node: ast.arguments) -> Any:
        valid = (
            (len(node.posonlyargs) == 0) and
            (len(node.args) == 0) and
            (len(node.kwonlyargs) == 0) and
            (not node.vararg) and
            (not node.kwarg)
        )
        assert valid, 'Workflow functions should have no arguments.'
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        node.args.args.append(ast.arg(arg='__wf_env', annotation=None, type_comment=None))
        node.body = [self.generic_visit(child) for child in node.body]
        node.body.append(ast.Return(value=ast.Name(id='__wf_env', ctx=ast.Load())))
        return node

    def visit_Name(self, node: ast.Name) -> Any:
        # The following conditional is an approximation to the rule that
        # the environment consists of literals, while functions (and technically
        # classes) need to remain as they are so they are picked up by the
        # freezing process.
        if ((node.id not in self.visitor._module) or
            (not isinstance(self.visitor._module[node.id], Callable))):
            node = ast.Subscript(
                value=ast.Name(id='__wf_env', ctx=ast.Load()),
                slice=ast.Index(value=ast.Constant(value=node.id)),
                ctx=node.ctx
            )
        return node

    def visit_Return(self, node: ast.Return) -> Any:
        if not node.value:
            node.value = ast.Name(id='__wf_env', ctx=ast.Load())
        else:
            node = super().generic_visit(node)
        return node


def parse(file_obj: TextIO) -> ToplevelVisitor:
    '''Parse an input file object.
    '''
    file_path = os.path.abspath(file_obj.name)
    source = file_obj.read()
    tree = ast.parse(source, file_path, type_comments=True)
    code_obj = compile(tree, file_path, 'exec')
    module_dict = {'__file__': file_path}
    exec(code_obj, module_dict)
    visitor = ToplevelVisitor(module_dict)
    visitor.visit(tree)
    return visitor


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='flowc')
    parser.add_argument(
        'sources', metavar='source', nargs='*', type=open,
        help='input source file(s)'
    )
    parser.add_argument(
        '--log_level', nargs='?', default=logging.INFO, type=int,
        help=f'logging level (DEBUG={logging.DEBUG}, INFO={logging.INFO}...)'
    )
    parser.add_argument(
        ('--output_path', '-o'), nargs='?', default='./', type=str,
        help='path to create'
    )
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('flowc'), level=namespace.log_level)
    if len(namespace.sources) == 0:
        parse(sys.stdin)
    else:
        for source in namespace.sources:
            parse(source)
