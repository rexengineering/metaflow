'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

from .. import cmof

class Boolean(cmof.Element):
    _ns={'prefix': 'dc', 'localName': 'Boolean', 'name': 'dc:Boolean'}

class Bounds(cmof.Element):
    height: cmof.Real
    width: cmof.Real
    x: cmof.Real
    y: cmof.Real
    _ns={'prefix': 'dc', 'localName': 'Bounds', 'name': 'dc:Bounds'}

class Font(cmof.Element):
    isBold: cmof.Boolean
    isItalic: cmof.Boolean
    isStrikeThrough: cmof.Boolean
    isUnderline: cmof.Boolean
    name: cmof.String
    size: cmof.Real
    _ns={'prefix': 'dc', 'localName': 'Font', 'name': 'dc:Font'}

class Integer(cmof.Element):
    _ns={'prefix': 'dc', 'localName': 'Integer', 'name': 'dc:Integer'}

class Point(cmof.Element):
    x: cmof.Real
    y: cmof.Real
    _ns={'prefix': 'dc', 'localName': 'Point', 'name': 'dc:Point'}

class Real(cmof.Element):
    _ns={'prefix': 'dc', 'localName': 'Real', 'name': 'dc:Real'}

class String(cmof.Element):
    _ns={'prefix': 'dc', 'localName': 'String', 'name': 'dc:String'}

PACKAGE_METADATA = {'associations': [],
 'name': 'DC',
 'prefix': 'dc',
 'types': [{'name': 'Boolean'}, {'name': 'Integer'}, {'name': 'Real'},
           {'name': 'String'},
           {'name': 'Font',
            'properties': [{'isAttr': True,
                            'name': 'dc:name',
                            'ns': {'localName': 'name',
                                   'name': 'dc:name',
                                   'prefix': 'dc'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'dc:size',
                            'ns': {'localName': 'size',
                                   'name': 'dc:size',
                                   'prefix': 'dc'},
                            'type': 'Real'},
                           {'isAttr': True,
                            'name': 'dc:isBold',
                            'ns': {'localName': 'isBold',
                                   'name': 'dc:isBold',
                                   'prefix': 'dc'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'dc:isItalic',
                            'ns': {'localName': 'isItalic',
                                   'name': 'dc:isItalic',
                                   'prefix': 'dc'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'dc:isUnderline',
                            'ns': {'localName': 'isUnderline',
                                   'name': 'dc:isUnderline',
                                   'prefix': 'dc'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'name': 'dc:isStrikeThrough',
                            'ns': {'localName': 'isStrikeThrough',
                                   'name': 'dc:isStrikeThrough',
                                   'prefix': 'dc'},
                            'type': 'Boolean'}]},
           {'name': 'Point',
            'properties': [{'default': '0',
                            'isAttr': True,
                            'name': 'dc:x',
                            'ns': {'localName': 'x',
                                   'name': 'dc:x',
                                   'prefix': 'dc'},
                            'type': 'Real'},
                           {'default': '0',
                            'isAttr': True,
                            'name': 'dc:y',
                            'ns': {'localName': 'y',
                                   'name': 'dc:y',
                                   'prefix': 'dc'},
                            'type': 'Real'}]},
           {'name': 'Bounds',
            'properties': [{'default': '0',
                            'isAttr': True,
                            'name': 'dc:x',
                            'ns': {'localName': 'x',
                                   'name': 'dc:x',
                                   'prefix': 'dc'},
                            'type': 'Real'},
                           {'default': '0',
                            'isAttr': True,
                            'name': 'dc:y',
                            'ns': {'localName': 'y',
                                   'name': 'dc:y',
                                   'prefix': 'dc'},
                            'type': 'Real'},
                           {'isAttr': True,
                            'name': 'dc:width',
                            'ns': {'localName': 'width',
                                   'name': 'dc:width',
                                   'prefix': 'dc'},
                            'type': 'Real'},
                           {'isAttr': True,
                            'name': 'dc:height',
                            'ns': {'localName': 'height',
                                   'name': 'dc:height',
                                   'prefix': 'dc'},
                            'type': 'Real'}]}],
 'uri': 'http://www.omg.org/spec/DD/20100524/DC'}

registry = cmof.Registry([
    Boolean,
    Bounds,
    Font,
    Integer,
    Point,
    Real,
    String,
], package_map = {'dc': PACKAGE_METADATA})
