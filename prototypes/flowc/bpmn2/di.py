'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

from .. import cmof

class Diagram(cmof.Element):
    documentation: cmof.String
    id: cmof.String
    name: cmof.String
    resolution: cmof.Real
    _contents: Union['DiagramElement', List['Style']]
    _ns={'prefix': 'di', 'localName': 'Diagram', 'name': 'di:Diagram'}

class DiagramElement(cmof.Element):
    id: cmof.String
    _contents: Union['Extension', List['DiagramElement'], cmof.Ref['DiagramElement'], cmof.Ref['Style'], cmof.Ref[Diagram], cmof.Ref[cmof.Element]]
    _ns={'prefix': 'di', 'localName': 'DiagramElement', 'name': 'di:DiagramElement'}

class Extension(cmof.Element):
    _contents: List[cmof.Element]
    _ns={'prefix': 'di', 'localName': 'Extension', 'name': 'di:Extension'}

class Style(cmof.Element):
    id: cmof.String
    _ns={'prefix': 'di', 'localName': 'Style', 'name': 'di:Style'}

class Edge(DiagramElement):
    _contents: Union[List['dc.Point'], cmof.Ref[DiagramElement]]
    _ns={'prefix': 'di', 'localName': 'Edge', 'name': 'di:Edge'}

class Node(DiagramElement):
    _ns={'prefix': 'di', 'localName': 'Node', 'name': 'di:Node'}

class Label(Node):
    _contents: 'dc.Bounds'
    _ns={'prefix': 'di', 'localName': 'Label', 'name': 'di:Label'}

class LabeledEdge(Edge):
    _contents: List[Label]
    _ns={'prefix': 'di', 'localName': 'LabeledEdge', 'name': 'di:LabeledEdge'}

class Plane(Node):
    _contents: List[DiagramElement]
    _ns={'prefix': 'di', 'localName': 'Plane', 'name': 'di:Plane'}

class Shape(Node):
    _contents: 'dc.Bounds'
    _ns={'prefix': 'di', 'localName': 'Shape', 'name': 'di:Shape'}

class LabeledShape(Shape):
    _contents: List[Label]
    _ns={'prefix': 'di', 'localName': 'LabeledShape', 'name': 'di:LabeledShape'}

class Bounds(cmof.Property):
    value: 'dc.Bounds'
    _ns={'name': 'di:bounds', 'prefix': 'di', 'localName': 'bounds'}

class Extension(cmof.Property):
    value: Extension
    _ns={'name': 'di:extension', 'prefix': 'di', 'localName': 'extension'}

class ModelElement(cmof.Property):
    value: cmof.Element
    _ns={'name': 'di:modelElement', 'prefix': 'di', 'localName': 'modelElement'}

class OwnedElement(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:ownedElement', 'prefix': 'di', 'localName': 'ownedElement'}

class OwnedLabel(cmof.Property):
    value: Label
    _ns={'name': 'di:ownedLabel', 'prefix': 'di', 'localName': 'ownedLabel'}

class OwnedStyle(cmof.Property):
    value: Style
    _ns={'name': 'di:ownedStyle', 'prefix': 'di', 'localName': 'ownedStyle'}

class OwningDiagram(cmof.Property):
    value: Diagram
    _ns={'name': 'di:owningDiagram', 'prefix': 'di', 'localName': 'owningDiagram'}

class OwningElement(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:owningElement', 'prefix': 'di', 'localName': 'owningElement'}

class PlaneElement(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:planeElement', 'prefix': 'di', 'localName': 'planeElement'}

class RootElement(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:rootElement', 'prefix': 'di', 'localName': 'rootElement'}

class Source(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:source', 'prefix': 'di', 'localName': 'source'}

class Style(cmof.Property):
    value: Style
    _ns={'name': 'di:style', 'prefix': 'di', 'localName': 'style'}

class Target(cmof.Property):
    value: DiagramElement
    _ns={'name': 'di:target', 'prefix': 'di', 'localName': 'target'}

class Values(cmof.Property):
    value: cmof.Element
    _ns={'name': 'di:values', 'prefix': 'di', 'localName': 'values'}

class Waypoint(cmof.Property):
    value: 'dc.Point'
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'di:waypoint', 'prefix': 'di', 'localName': 'waypoint'}

PACKAGE_METADATA = {'associations': [],
 'name': 'DI',
 'prefix': 'di',
 'types': [{'isAbstract': True,
            'name': 'DiagramElement',
            'properties': [{'isAttr': True,
                            'isId': True,
                            'name': 'di:id',
                            'ns': {'localName': 'id',
                                   'name': 'di:id',
                                   'prefix': 'di'},
                            'type': 'String'},
                           {'name': 'di:extension',
                            'ns': {'localName': 'extension',
                                   'name': 'di:extension',
                                   'prefix': 'di'},
                            'type': 'di:Extension'},
                           {'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:owningDiagram',
                            'ns': {'localName': 'owningDiagram',
                                   'name': 'di:owningDiagram',
                                   'prefix': 'di'},
                            'type': 'di:Diagram'},
                           {'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:owningElement',
                            'ns': {'localName': 'owningElement',
                                   'name': 'di:owningElement',
                                   'prefix': 'di'},
                            'type': 'di:DiagramElement'},
                           {'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:modelElement',
                            'ns': {'localName': 'modelElement',
                                   'name': 'di:modelElement',
                                   'prefix': 'di'},
                            'type': 'Element'},
                           {'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:style',
                            'ns': {'localName': 'style',
                                   'name': 'di:style',
                                   'prefix': 'di'},
                            'type': 'di:Style'},
                           {'isMany': True,
                            'isReadOnly': True,
                            'isVirtual': True,
                            'name': 'di:ownedElement',
                            'ns': {'localName': 'ownedElement',
                                   'name': 'di:ownedElement',
                                   'prefix': 'di'},
                            'type': 'di:DiagramElement'}]},
           {'isAbstract': True,
            'name': 'Node',
            'superClass': ['DiagramElement']},
           {'isAbstract': True,
            'name': 'Edge',
            'properties': [{'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:source',
                            'ns': {'localName': 'source',
                                   'name': 'di:source',
                                   'prefix': 'di'},
                            'type': 'di:DiagramElement'},
                           {'isReadOnly': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'di:target',
                            'ns': {'localName': 'target',
                                   'name': 'di:target',
                                   'prefix': 'di'},
                            'type': 'di:DiagramElement'},
                           {'isMany': True,
                            'isUnique': False,
                            'name': 'di:waypoint',
                            'ns': {'localName': 'waypoint',
                                   'name': 'di:waypoint',
                                   'prefix': 'di'},
                            'type': 'dc:Point',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['DiagramElement']},
           {'isAbstract': True,
            'name': 'Diagram',
            'properties': [{'isAttr': True,
                            'isId': True,
                            'name': 'di:id',
                            'ns': {'localName': 'id',
                                   'name': 'di:id',
                                   'prefix': 'di'},
                            'type': 'String'},
                           {'isReadOnly': True,
                            'isVirtual': True,
                            'name': 'di:rootElement',
                            'ns': {'localName': 'rootElement',
                                   'name': 'di:rootElement',
                                   'prefix': 'di'},
                            'type': 'di:DiagramElement'},
                           {'isAttr': True,
                            'name': 'di:name',
                            'ns': {'localName': 'name',
                                   'name': 'di:name',
                                   'prefix': 'di'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'di:documentation',
                            'ns': {'localName': 'documentation',
                                   'name': 'di:documentation',
                                   'prefix': 'di'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'di:resolution',
                            'ns': {'localName': 'resolution',
                                   'name': 'di:resolution',
                                   'prefix': 'di'},
                            'type': 'Real'},
                           {'isMany': True,
                            'isReadOnly': True,
                            'isVirtual': True,
                            'name': 'di:ownedStyle',
                            'ns': {'localName': 'ownedStyle',
                                   'name': 'di:ownedStyle',
                                   'prefix': 'di'},
                            'type': 'di:Style'}]},
           {'isAbstract': True,
            'name': 'Shape',
            'properties': [{'name': 'di:bounds',
                            'ns': {'localName': 'bounds',
                                   'name': 'di:bounds',
                                   'prefix': 'di'},
                            'type': 'dc:Bounds'}],
            'superClass': ['Node']},
           {'isAbstract': True,
            'name': 'Plane',
            'properties': [{'isMany': True,
                            'name': 'di:planeElement',
                            'ns': {'localName': 'planeElement',
                                   'name': 'di:planeElement',
                                   'prefix': 'di'},
                            'subsettedProperty': 'DiagramElement-ownedElement',
                            'type': 'di:DiagramElement'}],
            'superClass': ['Node']},
           {'isAbstract': True,
            'name': 'LabeledEdge',
            'properties': [{'isMany': True,
                            'isReadOnly': True,
                            'isVirtual': True,
                            'name': 'di:ownedLabel',
                            'ns': {'localName': 'ownedLabel',
                                   'name': 'di:ownedLabel',
                                   'prefix': 'di'},
                            'subsettedProperty': 'DiagramElement-ownedElement',
                            'type': 'di:Label'}],
            'superClass': ['Edge']},
           {'isAbstract': True,
            'name': 'LabeledShape',
            'properties': [{'isMany': True,
                            'isReadOnly': True,
                            'isVirtual': True,
                            'name': 'di:ownedLabel',
                            'ns': {'localName': 'ownedLabel',
                                   'name': 'di:ownedLabel',
                                   'prefix': 'di'},
                            'subsettedProperty': 'DiagramElement-ownedElement',
                            'type': 'di:Label'}],
            'superClass': ['Shape']},
           {'isAbstract': True,
            'name': 'Label',
            'properties': [{'name': 'di:bounds',
                            'ns': {'localName': 'bounds',
                                   'name': 'di:bounds',
                                   'prefix': 'di'},
                            'type': 'dc:Bounds'}],
            'superClass': ['Node']},
           {'isAbstract': True,
            'name': 'Style',
            'properties': [{'isAttr': True,
                            'isId': True,
                            'name': 'di:id',
                            'ns': {'localName': 'id',
                                   'name': 'di:id',
                                   'prefix': 'di'},
                            'type': 'String'}]},
           {'name': 'Extension',
            'properties': [{'isMany': True,
                            'name': 'di:values',
                            'ns': {'localName': 'values',
                                   'name': 'di:values',
                                   'prefix': 'di'},
                            'type': 'Element'}]}],
 'uri': 'http://www.omg.org/spec/DD/20100524/DI',
 'xml': {'tagAlias': 'lowerCase'}}

registry = cmof.Registry([
    Bounds,
    Diagram,
    DiagramElement,
    Edge,
    Extension,
    Label,
    LabeledEdge,
    LabeledShape,
    ModelElement,
    Node,
    OwnedElement,
    OwnedLabel,
    OwnedStyle,
    OwningDiagram,
    OwningElement,
    Plane,
    PlaneElement,
    RootElement,
    Shape,
    Source,
    Style,
    Target,
    Values,
    Waypoint,
], package_map = {'di': PACKAGE_METADATA})
