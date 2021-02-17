import collections
import tempfile
from typing import Mapping

import graphviz
import xmltodict

from .bpmn2 import bpmn, bpmndi, di
from .bounds import Bounds


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


def _map_process_to_svg(
        process: bpmn.Process,
        svg: collections.OrderedDict) -> Mapping[str, collections.OrderedDict]:
    result = {}
    bpmn_element_map = {
        getattr(bpmn_element, 'id') : (
            getattr(bpmn_element, 'sourceRef', None),
            getattr(bpmn_element, 'targetRef', None)
        )
        for bpmn_element in process
    }
    svg_contents = svg['svg']['g']['g']
    for svg_element in svg_contents:
        title = svg_element['title']
        if svg_element['@class'] == 'node':
            # Node...
            result[title] = svg_element
            bpmn_element_map.pop(title)
        else:
            # Edge...
            source, target = svg_element['title'].split('->')
            for bpmn_element_id, edge_attributes in bpmn_element_map.items():
                if (edge_attributes[0] == source and
                        edge_attributes[1] == target):
                    result[bpmn_element_id] = svg_element
                    bpmn_element_map.pop(bpmn_element_id)
                    break
    return result


def process_to_diagram(process: bpmn.Process) -> bpmndi.BPMNDiagram:
    digraph = bpmn_to_dot(process)
    svg = dot_to_svg(digraph)
    result = bpmndi.BPMNDiagram(id='BPMNDiagram_1')
    plane = bpmndi.BPMNPlane(bpmnElement=process.id, id='BPMNPlane_1')
    svg_map = _map_process_to_svg(process, svg)
    for bpmn_element in process:
        bpmn_element_id = getattr(bpmn_element, 'id', '???')
        if bpmn_element_id in svg_map:
            svg_element = svg_map[bpmn_element_id]
            attrs = dict(
                bpmnElement=bpmn_element_id,
                id=f'{bpmn_element_id}_di'
            )
            if isinstance(bpmn_element, (bpmn.SequenceFlow, bpmn.Association)):
                # Make edge...
                diagram_element = bpmndi.BPMNEdge(**attrs)
            else:
                # Make node...
                diagram_element = bpmndi.BPMNShape(**attrs)
                bounds = Bounds.from_g(svg_element)
                diagram_element.append(bounds.to_dc_bounds())
                if 'text' in svg_element:
                    bpmn_label = bpmndi.BPMNLabel()
                    label_bounds = Bounds.from_text(svg_element['text'])
                    bpmn_label.append(label_bounds.to_dc_bounds())
                    diagram_element.append(bpmn_label)
            plane.append(diagram_element)
    result.append(plane)
    return result
