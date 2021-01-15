'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

from .. import cmof
try:
    import di
except ImportError:
    from . import di


class ParticipantBandKind(cmof.Enum):
    top_initiating='top_initiating'
    middle_initiating='middle_initiating'
    bottom_initiating='bottom_initiating'
    top_non_initiating='top_non_initiating'
    middle_non_initiating='middle_non_initiating'
    bottom_non_initiating='bottom_non_initiating'
ParticipantBandKind._ns={'prefix': 'bpmndi', 'localName': 'ParticipantBandKind', 'name': 'bpmndi:ParticipantBandKind'}

class MessageVisibleKind(cmof.Enum):
    initiating='initiating'
    non_initiating='non_initiating'
MessageVisibleKind._ns={'prefix': 'bpmndi', 'localName': 'MessageVisibleKind', 'name': 'bpmndi:MessageVisibleKind'}

class BPMNDiagram(di.Diagram):
    _contents: Union['BPMNPlane', List['BPMNLabelStyle']]
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNDiagram', 'name': 'bpmndi:BPMNDiagram'}

class BPMNEdge(di.LabeledEdge):
    bpmnElement: 'bpmn.BaseElement'
    messageVisibleKind: MessageVisibleKind
    sourceElement: 'di.DiagramElement'
    targetElement: 'di.DiagramElement'
    _contents: 'BPMNLabel'
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNEdge', 'name': 'bpmndi:BPMNEdge'}

class BPMNLabel(di.Label):
    labelStyle: 'BPMNLabelStyle'
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNLabel', 'name': 'bpmndi:BPMNLabel'}

class BPMNLabelStyle(di.Style):
    _contents: 'dc.Font'
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNLabelStyle', 'name': 'bpmndi:BPMNLabelStyle'}

class BPMNPlane(di.Plane):
    bpmnElement: 'bpmn.BaseElement'
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNPlane', 'name': 'bpmndi:BPMNPlane'}

class BPMNShape(di.LabeledShape):
    bpmnElement: 'bpmn.BaseElement'
    choreographyActivityShape: 'BPMNShape'
    isExpanded: cmof.Boolean
    isHorizontal: cmof.Boolean
    isMarkerVisible: cmof.Boolean
    isMessageVisible: cmof.Boolean
    participantBandKind: ParticipantBandKind
    _contents: BPMNLabel
    _ns={'prefix': 'bpmndi', 'localName': 'BPMNShape', 'name': 'bpmndi:BPMNShape'}

class Font(cmof.Property):
    value: 'dc.Font'
    _ns={'name': 'bpmndi:font', 'prefix': 'bpmndi', 'localName': 'font'}

class Label(cmof.Property):
    value: BPMNLabel
    _ns={'name': 'bpmndi:label', 'prefix': 'bpmndi', 'localName': 'label'}

class LabelStyle(cmof.Property):
    value: BPMNLabelStyle
    _ns={'name': 'bpmndi:labelStyle', 'prefix': 'bpmndi', 'localName': 'labelStyle'}

class Plane(cmof.Property):
    value: BPMNPlane
    _ns={'name': 'bpmndi:plane', 'prefix': 'bpmndi', 'localName': 'plane'}

PACKAGE_METADATA = {'associations': [],
 'enumerations': [{'literalValues': [{'name': 'top_initiating'},
                                     {'name': 'middle_initiating'},
                                     {'name': 'bottom_initiating'},
                                     {'name': 'top_non_initiating'},
                                     {'name': 'middle_non_initiating'},
                                     {'name': 'bottom_non_initiating'}],
                   'name': 'ParticipantBandKind'},
                  {'literalValues': [{'name': 'initiating'},
                                     {'name': 'non_initiating'}],
                   'name': 'MessageVisibleKind'}],
 'name': 'BPMNDI',
 'prefix': 'bpmndi',
 'types': [{'name': 'BPMNDiagram',
            'properties': [{'name': 'bpmndi:plane',
                            'ns': {'localName': 'plane',
                                   'name': 'bpmndi:plane',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:Diagram#rootElement',
                            'type': 'bpmndi:BPMNPlane'},
                           {'isMany': True,
                            'name': 'bpmndi:labelStyle',
                            'ns': {'localName': 'labelStyle',
                                   'name': 'bpmndi:labelStyle',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:BPMNLabelStyle'}],
            'superClass': ['di:Diagram']},
           {'name': 'BPMNPlane',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:bpmnElement',
                            'ns': {'localName': 'bpmnElement',
                                   'name': 'bpmndi:bpmnElement',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:DiagramElement#modelElement',
                            'type': 'bpmn:BaseElement'}],
            'superClass': ['di:Plane']},
           {'name': 'BPMNShape',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:bpmnElement',
                            'ns': {'localName': 'bpmnElement',
                                   'name': 'bpmndi:bpmnElement',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:DiagramElement#modelElement',
                            'type': 'bpmn:BaseElement'},
                           {'isAttr': True,
                            'name': 'bpmndi:isHorizontal',
                            'ns': {'localName': 'isHorizontal',
                                   'name': 'bpmndi:isHorizontal',
                                   'prefix': 'bpmndi'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'bpmndi:isExpanded',
                            'ns': {'localName': 'isExpanded',
                                   'name': 'bpmndi:isExpanded',
                                   'prefix': 'bpmndi'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'bpmndi:isMarkerVisible',
                            'ns': {'localName': 'isMarkerVisible',
                                   'name': 'bpmndi:isMarkerVisible',
                                   'prefix': 'bpmndi'},
                            'type': 'Boolean'},
                           {'name': 'bpmndi:label',
                            'ns': {'localName': 'label',
                                   'name': 'bpmndi:label',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:BPMNLabel'},
                           {'isAttr': True,
                            'name': 'bpmndi:isMessageVisible',
                            'ns': {'localName': 'isMessageVisible',
                                   'name': 'bpmndi:isMessageVisible',
                                   'prefix': 'bpmndi'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'bpmndi:participantBandKind',
                            'ns': {'localName': 'participantBandKind',
                                   'name': 'bpmndi:participantBandKind',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:ParticipantBandKind'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:choreographyActivityShape',
                            'ns': {'localName': 'choreographyActivityShape',
                                   'name': 'bpmndi:choreographyActivityShape',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:BPMNShape'}],
            'superClass': ['di:LabeledShape']},
           {'name': 'BPMNEdge',
            'properties': [{'name': 'bpmndi:label',
                            'ns': {'localName': 'label',
                                   'name': 'bpmndi:label',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:BPMNLabel'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:bpmnElement',
                            'ns': {'localName': 'bpmnElement',
                                   'name': 'bpmndi:bpmnElement',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:DiagramElement#modelElement',
                            'type': 'bpmn:BaseElement'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:sourceElement',
                            'ns': {'localName': 'sourceElement',
                                   'name': 'bpmndi:sourceElement',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:Edge#source',
                            'type': 'di:DiagramElement'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:targetElement',
                            'ns': {'localName': 'targetElement',
                                   'name': 'bpmndi:targetElement',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:Edge#target',
                            'type': 'di:DiagramElement'},
                           {'default': 'initiating',
                            'isAttr': True,
                            'name': 'bpmndi:messageVisibleKind',
                            'ns': {'localName': 'messageVisibleKind',
                                   'name': 'bpmndi:messageVisibleKind',
                                   'prefix': 'bpmndi'},
                            'type': 'bpmndi:MessageVisibleKind'}],
            'superClass': ['di:LabeledEdge']},
           {'name': 'BPMNLabel',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmndi:labelStyle',
                            'ns': {'localName': 'labelStyle',
                                   'name': 'bpmndi:labelStyle',
                                   'prefix': 'bpmndi'},
                            'redefines': 'di:DiagramElement#style',
                            'type': 'bpmndi:BPMNLabelStyle'}],
            'superClass': ['di:Label']},
           {'name': 'BPMNLabelStyle',
            'properties': [{'name': 'bpmndi:font',
                            'ns': {'localName': 'font',
                                   'name': 'bpmndi:font',
                                   'prefix': 'bpmndi'},
                            'type': 'dc:Font'}],
            'superClass': ['di:Style']}],
 'uri': 'http://www.omg.org/spec/BPMN/20100524/DI'}

registry = cmof.Registry([
    BPMNDiagram,
    BPMNEdge,
    BPMNLabel,
    BPMNLabelStyle,
    BPMNPlane,
    BPMNShape,
    Font,
    Label,
    LabelStyle,
    MessageVisibleKind,
    ParticipantBandKind,
    Plane,
], package_map = {'bpmndi': PACKAGE_METADATA})
