import ast
from typing import Any, NamedTuple


class ServiceTaskCall(NamedTuple):
    task_name: str
    index: int
    call_site: ast.Call

    @property
    def service_name(self) -> str:
        return f'{self.task_name}_{self.index}'


class WorkflowVisitor(ast.NodeVisitor):
    def __init__(self, module: dict) -> None:
        self.module = module
        self.task_map = {
            key: value for key, value in module.items()
            if hasattr(value, '_service_task')
        }
        self.tasks = []
        super().__init__()

    def visit_Call(self, node: ast.Call) -> Any:
        # Visit children first.
        result = super().generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.task_map:
            self.tasks.append(
                ServiceTaskCall(node.func.id, len(self.tasks) + 1, node)
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
