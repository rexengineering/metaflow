import ast
from typing import List, NamedTuple, Optional, Union


class CFGJump(NamedTuple):
    branch: int


class CFGBranch(NamedTuple):
    predicate: ast.expr
    true_branch: int
    false_branch: int


class CFGReturn(NamedTuple):
    returns: ast.Return


class CFGBlock:
    index: int
    statements: List[ast.stmt]
    terminal: Optional[Union[CFGJump, CFGBranch, CFGReturn]]

    def __init__(
            self,
            index: int,
            statements: List[ast.stmt],
            terminal: Optional[Union[CFGJump, CFGBranch, CFGReturn]] = None):
        self.index = index
        self.statements = statements
        self.terminal = terminal


def dump_blocks(blocks: List[CFGBlock]) -> str:
    lns = []
    for block in blocks:
        lns.append(f'block {block.index}:')
        for stmt in block.statements:
            lns.append(f'    {ast.dump(stmt)}')
        lns.append(f'    {block.terminal}\n')
    return '\n'.join(lns)


class CFGTransfomer(ast.NodeVisitor):
    function: ast.FunctionDef
    blocks: List[Optional[CFGBlock]]
    current_block: Optional[CFGBlock]

    def __init__(self, function: ast.FunctionDef):
        self.function = function
        self.blocks = []

    def new_block(self):
        result = CFGBlock(len(self.blocks), [], None)
        self.blocks.append(result)
        return result

    def get_cfg(self):
        self.blocks = []
        self.visit(self.function)
        return self.blocks

    def unsupported(self, _):
        raise NotImplementedError('Unsupported Python construct.')

    def generic_stmt(self, node: ast.stmt):
        assert self.current_block is not None, 'Internal error: the CFG ' \
            'transformer is not currently pointing at a basic block.'
        self.current_block.statements.append(node)

    def _eliminate_dead_code(self):
        in_counts = {0: 1}
        in_counts.update((block.index, 0) for block in self.blocks[1:])
        for block in self.blocks[1:]:
            terminal = block.terminal
            assert terminal is not None, 'Internal error: unterminated ' \
                'basic block detected during dead code elimination.'
            if isinstance(terminal, CFGJump):
                in_counts[terminal.branch] += 1
            elif isinstance(terminal, CFGBranch):
                in_counts[terminal.true_branch] += 1
                in_counts[terminal.false_branch] += 1
        for block_index, in_count in in_counts.items():
            if in_count < 1:
                if block_index == len(self.blocks) - 1:
                    self.blocks.pop()
                else:
                    self.blocks[block_index] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        assert len(self.blocks) == 0, 'Nested functions in a workflow are ' \
            'not supported.'
        self.current_block = self.new_block()
        self.generic_visit(node)
        assert self.current_block == self.blocks[-1], 'Internal error: the ' \
            'CFG transformer is not pointing at the tail block ' \
            f'({self.current_block}).'
        if not isinstance(self.current_block.terminal, CFGReturn):
            assert self.current_block.terminal is None, 'Internal error: ' \
                'tail block in function does not end in a return.'
            self.current_block.terminal = CFGReturn(ast.Return(value=None))
        self.current_block = None
        self._eliminate_dead_code()

    visit_AsyncFunctionDef = unsupported
    visit_ClassDef = unsupported

    def visit_Return(self, node: ast.Return):
        assert self.current_block.terminal is None, 'Internal error: I have ' \
            'hit a return statement within a basic block that is already ' \
            'terminated.'
        self.current_block.terminal = CFGReturn(node)
        self.current_block = self.new_block()

    visit_Delete = generic_stmt
    visit_Assign = generic_stmt
    visit_AugAssign = generic_stmt
    visit_AnnAssign = generic_stmt

    visit_For = unsupported  # TODO
    visit_AsyncFor = unsupported
    visit_While = unsupported  # TODO

    def visit_If(self, node: ast.If):
        if_block = self.current_block
        assert if_block.terminal is None
        true_branch = -1
        if len(node.body) > 0:
            self.current_block = self.new_block()
            true_branch = self.current_block.index
            for stmt in node.body:
                self.visit(stmt)
        true_tail = self.current_block
        false_branch = -1
        if len(node.orelse) > 0:
            self.current_block = self.new_block()
            false_branch = self.current_block.index
            for stmt in node.orelse:
                self.visit(stmt)
        false_tail = self.current_block
        join_block = self.new_block()
        if true_tail != if_block:
            if true_tail.terminal is None:
                true_tail.terminal = CFGJump(join_block.index)
        if true_branch < 0:
            true_branch = join_block.index
        if false_tail != if_block:
            if false_tail.terminal is None:
                false_tail.terminal = CFGJump(join_block.index)
        if false_branch < 0:
            false_branch = join_block.index
        if_block.terminal = CFGBranch(node.test, true_branch, false_branch)
        self.current_block = join_block

    visit_With = unsupported  # TODO
    visit_AsyncWith = unsupported
    visit_Raise = unsupported
    visit_Try = unsupported

    visit_Assert = generic_stmt
    visit_Import = generic_stmt
    visit_ImportFrom = generic_stmt
    visit_Global = generic_stmt
    visit_Nonlocal = generic_stmt
    visit_Expr = generic_stmt
    visit_Pass = generic_stmt

    visit_Break = unsupported  # TODO
    visit_Continue = unsupported  # TODO
