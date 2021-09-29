'''Top-level workflow code generator.
'''


import ast
from typing import Dict, List, Optional

from . import bpmn_to_dot, cfg, toplevel, visitors
from .bpmn2 import bpmn, registry
from .intcounter import IntCounter


def _make_edge(
        source: bpmn.BaseElement,
        target: bpmn.BaseElement,
        counter: IntCounter,
        **attributes: Dict[str, str]) -> bpmn.SequenceFlow:
    '''Make a sequence flow element from source to target.
    '''
    sequence_flow = bpmn.SequenceFlow(
        id=f'SequenceFlow_{counter.postinc}',
        sourceRef=source.id,
        targetRef=target.id,
        **attributes
    )
    source.append(bpmn.Outgoing(sequence_flow.id))
    target.append(bpmn.Incoming(sequence_flow.id))
    return sequence_flow


def _task_to_bpmn(
        call: visitors.ServiceTaskCall,
        counter: IntCounter) -> bpmn.ServiceTask:
    '''Create a new service task for the given call to a function marked as
    being a service task.
    '''
    service_task = bpmn.ServiceTask(
        id=f'Task_{counter.postinc}', name=call.service_name
    )
    return service_task

def _stmt_to_call(node: ast.stmt) -> ast.Call:
    '''Type safety utility to ensure a given AST node is supported by FlowC.

    Raises a ValueError if the given AST node is unsupported.
    '''
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        if isinstance(node.value, ast.Call):
            return node.value
    elif isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Call):
            return node.value
    raise ValueError(f'Unsupported AST node: {ast.dump(node)}')


def generate_bpmn_process(visitor: toplevel.ToplevelVisitor) -> bpmn.Process:
    counter = IntCounter()
    assert visitor.workflow is not None, 'No workflow function in toplevel ' \
        'visitor.'
    process = bpmn.Process(id=visitor.workflow.name, isExecutable=True)

    # First create the BPMN elements...
    start_event = bpmn.StartEvent(
        id=f'StartEvent_{counter.postinc}', name='Start'
    )
    process.append(start_event)
    service_task_map: Dict[ast.Call, bpmn.ServiceTask] = {
        task.call_site : _task_to_bpmn(task, counter)
        for task in visitor.tasks
    }
    process.extend(service_task_map.values())
    block_map: Dict[int, List[bpmn.BaseElement]] = {}
    for block in visitor.blocks:
        if block is not None:
            block_map[block.index] = [
                service_task_map[_stmt_to_call(statement)]
                for statement in block.statements
            ]
            gateway: Optional[bpmn.Gateway] = None
            if cfg.CFGFlags.BRANCH_JOIN in block.flags:
                assert block.index != 0
                assert cfg.CFGFlags.FORK_JOIN not in block.flags, 'Basic ' \
                    'block joins both a branch and a fork.'
                gateway = bpmn.ExclusiveGateway(
                    id=f'ExclusiveGateway_{counter.postinc}'
                )
            elif cfg.CFGFlags.FORK_JOIN in block.flags:
                gateway = bpmn.ParallelGateway(
                    id=f'ParallelGateway_{counter.postinc}'
                )
            if gateway is not None:
                process.append(gateway)
                block_map[block.index].insert(0, gateway)

    # Then, link them together with edges...
    sequence_flows = [_make_edge(
        start_event, service_task_map[visitor.tasks[0].call_site], counter
    )]
    for block_index, block_elements in block_map.items():
        block = visitor.blocks[block_index]
        assert block is not None, 'Block map should not index dead code.'
        current = block_elements[0]
        for next in block_elements[1:]:
            sequence_flows.append(_make_edge(current, next, counter))
            current = next
        if isinstance(block.terminal, cfg.CFGJump):
            target_element = block_map[block.terminal.branch][0]
            sequence_flows.append(_make_edge(current, target_element, counter))
        elif isinstance(block.terminal, cfg.CFGBranch):
            false_target = block_map[block.terminal.false_branch][0]
            gateway = next = bpmn.ExclusiveGateway(
                id=f'ExclusiveGateway_{counter.postinc}',
            )
            process.append(next)
            sequence_flows.append(_make_edge(current, next, counter))
            current = next
            # FIXME: Label the branch edges appropriately for REXFlow.
            true_branch = _make_edge(
                current, block_map[block.terminal.true_branch][0], counter
            )
            #true_branch.append(bpmn.ConditionExpression())
            sequence_flows.append(true_branch)
            false_branch = _make_edge(current, false_target, counter)
            sequence_flows.append(false_branch)
            gateway.default = false_branch.id
        elif isinstance(block.terminal, cfg.CFGReturn):
            # FIXME: How do we handle a return statement with an expression?
            next = bpmn.EndEvent(id=f'EndEvent_{counter.postinc}')
            process.append(next)
            sequence_flows.append(_make_edge(current, next, counter))
        else:
            assert isinstance(block.terminal, cfg.CFGFork)
            next = bpmn.ParallelGateway(
                id=f'ParallelGateway_{counter.postinc}'
            )
            process.append(next)
            sequence_flows.append(_make_edge(current, next, counter))
            current = next
            sequence_flows.extend(
                _make_edge(current, block_map[target_index][0], counter)
                for target_index in block.terminal.branches
            )
    process.extend(sequence_flows)
    return process


def generate_bpmn(
        visitor: toplevel.ToplevelVisitor,
        include_diagram: bool = True) -> bpmn.Definitions:
    process = generate_bpmn_process(visitor)
    packages = registry.package_map
    attrs = {
        f'xmlns:{prefix}': package_data['uri']
        for prefix, package_data in packages.items()
    }
    attrs.update(exporter='REXFlow Compiler', exporterVersion='0.0.1')
    result = bpmn.Definitions([process], **attrs)
    if include_diagram:
        result.append(bpmn_to_dot.process_to_diagram(process))
    return result
