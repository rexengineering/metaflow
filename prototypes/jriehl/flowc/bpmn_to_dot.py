import collections
import tempfile

import graphviz
import xmltodict

from .bpmn2 import bpmn


def bpmn_to_dot(process: bpmn.Process) -> graphviz.Digraph:
    result = graphviz.Digraph(process.id)
    result.attr(rankdir='LR')
    result.attr('node', shape='box')
    for elem in process:
        if isinstance(elem, bpmn.SequenceFlow):
            result.edge(elem.sourceRef, elem.targetRef)
        else:
            element_identifier = getattr(elem, 'id', '???')
            attrs = {'label': getattr(elem, 'name', element_identifier)}
            if isinstance(elem, bpmn.StartEvent):
                attrs['shape'] = 'circle'
            elif isinstance(elem, bpmn.EndEvent):
                attrs['shape'] = 'doublecircle'
            result.node(element_identifier, **attrs)
    return result


def dot_to_xdot(digraph: graphviz.Digraph) -> graphviz.Source:
    digraph_path = digraph.render(
        directory=tempfile.gettempdir(),
        format='xdot'
    )
    return graphviz.Source.from_file(digraph_path)


def dot_to_svg(digraph: graphviz.Digraph) -> collections.OrderedDict:
    digraph_path = str(digraph.render(
        directory=tempfile.gettempdir(),
        format='svg'
    ))
    with open(digraph_path, 'rb') as digraph_file:
        result = xmltodict.parse(digraph_file)
        assert isinstance(result, collections.OrderedDict)
    return result
