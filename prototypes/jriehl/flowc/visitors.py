import ast
from typing import Any, Dict, List, NamedTuple, Optional


class ServiceTaskCall(NamedTuple):
    task_name: str
    index: int
    call_site: ast.Call
    targets: Optional[List[ast.expr]]
    args: List[ast.expr]
    keywords: List[ast.keyword]

    @property
    def service_name(self) -> str:
        return f'{self.task_name}_{self.index}'


class WorkflowVisitor(ast.NodeVisitor):
    def __init__(self, module: Dict[str, Any]) -> None:
        self.module = module
        self.task_map = {
            key: value for key, value in module.items()
            if hasattr(value, '_service_task')
        }
        self.tasks: List[ServiceTaskCall] = []
        self.targets_stack: List[Optional[List[ast.expr]]] = [None]
        super().__init__()

    def visit_Assign(self, node: ast.Assign) -> Any:
        self.targets_stack.append(node.targets)
        result = super().generic_visit(node)
        self.targets_stack.pop()
        return result

    def visit_Call(self, node: ast.Call) -> Any:
        # Visit children first.
        result = super().generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.task_map:
            targets = (
                [
                    ast.fix_missing_locations(RewriteTargets().visit(target))
                    for target in self.targets_stack[-1]
                ]
                if self.targets_stack[-1] is not None else
                self.targets_stack[-1]
            )
            args = [
                ast.fix_missing_locations(RewriteTargets().visit(arg))
                for arg in node.args
            ]
            keywords = [
                ast.keyword(
                    keyword.arg,
                    ast.fix_missing_locations(RewriteTargets().visit(
                        keyword.value
                    ))
                )
                for keyword in node.keywords
            ]
            self.tasks.append(
                ServiceTaskCall(
                    task_name=node.func.id,
                    index=len(self.tasks) + 1,
                    call_site=node,
                    targets=targets,
                    args=args,
                    keywords=keywords
                )
            )
        return result

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.module:
            # We have a global name reference.
            if isinstance(node.ctx, (ast.Store, ast.AugStore, ast.Del)):
                raise ValueError(
                    f'Line {node.lineno}: reassignment and deletion of global '
                    f'{node.id} is not allowed by flowc.'
                )
        return super().generic_visit(node)


class RewriteTargets(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> Any:
        return ast.Subscript(
            value=ast.Name(id='environment', ctx=ast.Load()),
            slice=ast.Index(value=ast.Constant(value=node.id)),
            ctx=node.ctx
        )
