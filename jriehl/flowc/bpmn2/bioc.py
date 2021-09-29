'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

from .. import cmof

class ColoredEdge(cmof.Element):
    fill: cmof.String
    stroke: cmof.String
    _ns={'prefix': 'bioc', 'localName': 'ColoredEdge', 'name': 'bioc:ColoredEdge'}

class ColoredShape(cmof.Element):
    fill: cmof.String
    stroke: cmof.String
    _ns={'prefix': 'bioc', 'localName': 'ColoredShape', 'name': 'bioc:ColoredShape'}

PACKAGE_METADATA = {'associations': [],
 'enumerations': [],
 'name': 'bpmn.io colors for BPMN',
 'prefix': 'bioc',
 'types': [{'extends': ['bpmndi:BPMNShape'],
            'name': 'ColoredShape',
            'properties': [{'isAttr': True,
                            'name': 'bioc:stroke',
                            'ns': {'localName': 'stroke',
                                   'name': 'bioc:stroke',
                                   'prefix': 'bioc'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bioc:fill',
                            'ns': {'localName': 'fill',
                                   'name': 'bioc:fill',
                                   'prefix': 'bioc'},
                            'type': 'String'}]},
           {'extends': ['bpmndi:BPMNEdge'],
            'name': 'ColoredEdge',
            'properties': [{'isAttr': True,
                            'name': 'bioc:stroke',
                            'ns': {'localName': 'stroke',
                                   'name': 'bioc:stroke',
                                   'prefix': 'bioc'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bioc:fill',
                            'ns': {'localName': 'fill',
                                   'name': 'bioc:fill',
                                   'prefix': 'bioc'},
                            'type': 'String'}]}],
 'uri': 'http://bpmn.io/schema/bpmn/biocolor/1.0'}

registry = cmof.Registry([
    ColoredEdge,
    ColoredShape,
], package_map = {'bioc': PACKAGE_METADATA})
