'''Prototype support for CMOF metamodels.

Takes JSON inputs from NPM packages generated using Moddle-XML/Moddle.
(https://github.com/bpmn-io/moddle-xml, https://github.com/bpmn-io/moddle)

Example:

>>> import json, cmof
>>> bpmn_model = json.load(open('bpmn.json'))
>>> cmof.code_gen(bpmn_model, 'bpmn', file=open('bpmn.py', 'w'))
>>> import bpmn

Where `bpmn.json` was generated from the following Node session:

```node
> var bpmnModdle
> import('bpmn-moddle').then(module => { bpmnModdle = new module.default() })
> const fs = require('fs')
> fs.writeSync(fs.openSync('bpmn.json'),
... JSON.stringify(bpmnModdle.registry.packageMap.bpmn))
```
'''

import collections
import enum
from functools import reduce
import pprint
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, List, \
    NamedTuple, Optional, Set, TypeVar
import warnings
import weakref

import xmltodict

PY_3_8_KEYWORDS = [
    'False',
    'None',
    'True',
    'and',
    'as',
    'assert',
    'async',
    'await',
    'break',
    'class',
    'continue',
    'def',
    'del',
    'elif',
    'else',
    'except',
    'finally',
    'for',
    'from',
    'global',
    'if',
    'import',
    'in',
    'is',
    'lambda',
    'nonlocal',
    'not',
    'or',
    'pass',
    'raise',
    'return',
    'try',
    'while',
    'with',
    'yield'
]

PRELUDE = """'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

import {}
"""

Boolean = bool

Integer = int

Real = float

String = str


class NamespaceMetadataMixin:
    _registry: Callable[[], 'Registry']
    _ns = {}

    @classmethod
    def get_tag(cls) -> str:
        if '_tag' in cls.__dict__:
            return cls._tag
        if len(cls._ns) > 0:
            prefix = cls._ns['prefix']
            local_name = cls._ns['localName']
            if hasattr(cls, '_registry'):
                registry = cls._registry()
                if ((prefix in registry.package_map) and
                        ('xml' in (mdata := registry.package_map[prefix])) and
                        (mdata['xml'].get('tagAlias') == 'lowerCase')):
                    local_name = f'{local_name[0].lower()}{local_name[1:]}'
            result = f'{prefix}:{local_name}'
        else:
            result = cls.__name__
        cls._tag = result
        return result

    @property
    def tag(self) -> str:
        return self.get_tag()

    @classmethod
    def from_ordered_dict(cls, odict: collections.OrderedDict,
                          warn: bool = True
                          ) -> Optional['NamespaceMetadataMixin']:
        if hasattr(cls, '_registry'):
            return cls._registry().from_ordered_dict(
                cls.get_tag(), odict, warn
            )
        msg = f'{cls.__name__} has not been associated with a type registry.'
        if warn:
            warnings.warn(msg)
        else:
            raise ValueError(msg)
        return None

    @classmethod
    def from_xml(cls, xml: str, *args, warn: bool = True, **kws
                 ) -> Optional['NamespaceMetadataMixin']:
        if hasattr(cls, '_registry'):
            return cls._registry().from_xml(xml, *args, warn=warn, **kws)
        msg = f'{cls.__name__} has not been associated with a type registry.'
        if warn:
            warnings.warn(msg)
        else:
            raise ValueError(msg)
        return None


class ElementList(list, List['Element']):
    pass


class Element(list, List['Element'], NamespaceMetadataMixin):
    def __init__(self, elems: Iterable['Element'] = (), **kws) -> None:
        super().__init__(elems)
        for key, value in kws.items():
            setattr(self, key, value)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

    def to_ordered_dict(self) -> Optional[collections.OrderedDict]:
        result = None
        attributes = set(self.__dict__.keys())
        if (len(attributes) > 0) or (len(self) > 0):
            result = collections.OrderedDict()
            for attribute in sorted(attributes):
                result[f'@{attribute}'] = getattr(self, attribute)
            for child in self:
                if hasattr(child, 'tag'):
                    tag = child.tag
                    child_value = None
                    if isinstance(child, Element):
                        child_value = child.to_ordered_dict()
                    else:
                        child_value = child.value
                        if isinstance(child_value, Element):
                            if (hasattr(child, '_xml') and
                                    child._xml.get('serialize') == 'xsi:type'):
                                child_value = child_value.to_ordered_dict()
                            else:
                                child_value = collections.OrderedDict({
                                    child_value.tag:
                                        child_value.to_ordered_dict()
                                })
                    if tag in result:
                        elt_or_container = result[tag]
                        if isinstance(elt_or_container, ElementList):
                            elt_or_container.append(child_value)
                        else:
                            result[tag] = ElementList(
                                [elt_or_container, child_value]
                            )
                    else:
                        result[tag] = child_value
        return result

    def to_xml(self, *args, **kws):
        return xmltodict.unparse(collections.OrderedDict([
            (self.tag, self.to_ordered_dict())]), *args, **kws)


class Enum(NamespaceMetadataMixin, enum.Enum):
    pass


Referent = TypeVar('Referent')


class Ref(Generic[Referent]):
    def __init__(self, value: Optional[Referent]) -> None:
        self.ref = value

    @property
    def ref(self) -> Optional[Referent]:
        if self._ref is None:
            return None
        return self._ref()

    @ref.setter
    def ref(self, new: Optional[Referent]) -> None:
        if new is None:
            self._ref = None
        else:
            self._ref = weakref.ref(new)

    @ref.deleter
    def ref(self) -> None:
        self._ref = None

    @property
    def id(self) -> Optional[str]:
        ref = self.ref
        if hasattr(ref, 'id'):
            return ref.id
        return None


class PropertyTuple(NamedTuple):
    value: Any


class Property(PropertyTuple, NamespaceMetadataMixin):
    pass


class Registry(dict, Dict[str, type]):
    def __init__(self, types, package_map={}):
        super().__init__()
        self.package_map = package_map
        for type_obj in types:
            self.add(type_obj)

    def add(self, type_obj: type):
        assert issubclass(type_obj, NamespaceMetadataMixin)
        type_obj._registry = weakref.ref(self)
        self[type_obj.get_tag()] = type_obj

    def update(self, *args, **kws):
        super().update(*args, **kws)
        if len(args) > 0:
            self.package_map.update(getattr(args[0], 'package_map', {}))

    def _get_child_cls_from_annotations(self, parent: Property):
        value_cls = parent.__annotations__.get('value')
        if isinstance(value_cls, str):
            value_tag = value_cls.replace('.', ':')
            value_cls = self.get(value_tag)
        return value_cls

    def from_ordered_dict(self, tag: str, odict: collections.OrderedDict,
                          warn: bool = True):
        ctor = self.get(tag)
        if not ctor:
            msg = f'{repr(tag)} is not in this registry'
            if warn:
                warnings.warn(msg)
                return None
            else:
                raise ValueError(msg)
        attrs = {}
        children = []
        if (issubclass(ctor, Property) and
                hasattr(ctor, '_xml') and
                ctor._xml.get('serialize') == 'xsi:type'):
            value_cls = self._get_child_cls_from_annotations(ctor)
            if value_cls:
                children = self.from_ordered_dict(
                    value_cls.get_tag(), odict, warn
                )
        else:
            for key, value in odict.items():
                if key.startswith('@'):
                    attrs[key[1:]] = value
                elif isinstance(value, collections.OrderedDict):
                    children.append(self.from_ordered_dict(key, value, warn))
                elif isinstance(value, list):
                    children.extend(
                        self.from_ordered_dict(key, child, warn)
                        for child in value
                    )
                else:
                    child_type = self.get(key)
                    children.append(child_type(value))
        return ctor(children, **attrs)

    def from_xml(self, xml: str, *args, warn: bool = True, **kws):
        doc = xmltodict.parse(xml, *args, **kws)
        keys = tuple(doc.keys())
        assert len(keys) == 1
        key = keys[0]
        return self.from_ordered_dict(key, doc[key], warn)


def _avoid_python_keywords(candidate: str):
    if candidate in PY_3_8_KEYWORDS:
        return f'{candidate}_'
    return candidate


def _get_python_identifier(cmof_type_name: str,
                           namespace: Optional[str] = None,
                           already_defined: Optional[Set[str]] = None,
                           quote_char: str = "'"):
    if ':' in cmof_type_name:
        prefix, local_name = cmof_type_name.split(':')
        local_name = _avoid_python_keywords(local_name)
        if prefix == namespace:
            result = local_name
        else:
            result = f'{prefix}.{local_name}'
        if already_defined is not None and result not in already_defined:
            result = f'{quote_char}{result}{quote_char}'
    else:
        cmof_type_name = _avoid_python_keywords(cmof_type_name)
        result = f'cmof.{cmof_type_name}'
    return result


def toposort(digraph: Dict[Hashable, Set[Hashable]]):
    '''
    Adapted from https://code.activestate.com/recipes/577413-topological-sort/
    by Paddy McCarthy, licensed under the MIT License.
    '''
    for item, deps in digraph.items():
        deps.discard(item)  # Ignore self dependencies
    extra_items_in_deps = (
        reduce(set.union, digraph.values()) - set(digraph.keys())
    )
    digraph.update({item: set() for item in extra_items_in_deps})
    while True:
        ordered = set(item for item, deps in digraph.items() if not deps)
        if not ordered:
            break
        for item in sorted(ordered):
            yield item
        digraph = {item: (deps - ordered) for item, deps in digraph.items()
                   if item not in ordered}
    assert not digraph, "A cyclic dependency exists amongst %r" % digraph


def code_gen(cmof_json: dict, namespace: str, **kws):
    local_name_map = {}
    # Compute superclasses
    type_supers = {}  # type: Dict[str, List[str]]
    type_dependencies = {}
    imports = set(['cmof'])
    for type_defn in cmof_json['types']:
        local_name = type_defn['name']
        supers = [
            (_get_python_identifier(supertype, namespace)
                if ':' in supertype else
                supertype)
            for supertype in type_defn.get('superClass', [])
        ]
        imports.update([
            supertype.split('.')[0] for supertype in supers if '.' in supertype
        ])
        type_supers[local_name] = supers
        local_name_map[local_name] = type_defn
        type_dependencies[local_name] = set(supers)
    # Start emitting code
    print(PRELUDE.format(', '.join(imports)), **kws)
    defined_already = set()
    for enum_defn in cmof_json.get('enumerations', ()):
        enum_name = enum_defn['name']
        print(f'class {enum_name}(cmof.Enum):', **kws)
        for literal_value in enum_defn['literalValues']:
            value_name = literal_value['name']
            value_attr_name = _avoid_python_keywords(value_name)
            print(f'    {value_attr_name}={repr(value_name)}', **kws)
        namespace_metadata = {
            'prefix': namespace,
            'localName': enum_name,
            'name': f'{namespace}:{enum_name}'
        }
        print(f'{enum_name}._ns={repr(namespace_metadata)}\n', **kws)
        defined_already.add(enum_name)
    property_map = {}
    for name in toposort(type_dependencies):
        if name not in local_name_map:
            continue  # Skip anything defined outside the given namespace.
        local_name = name
        type_defn = local_name_map[local_name]
        supers = type_supers[local_name].copy()
        if not supers:
            supers.append('cmof.Element')
        print(f'class {local_name}({", ".join(supers)}):', **kws)
        type_properties = {
            prop['ns']['localName']: prop
            for prop in type_defn.get('properties', [])
        }
        ty_contains = set()
        for ty_prop_name in sorted(type_properties.keys()):
            ty_prop = type_properties[ty_prop_name]
            is_attr = ty_prop.get('isAttr')
            prop_type = _get_python_identifier(
                ty_prop['type'], namespace, defined_already
            )
            if is_attr:
                attr_name = _avoid_python_keywords(ty_prop_name)
                print(f'    {attr_name}: {prop_type}', **kws)
            else:
                property_map[ty_prop_name] = ty_prop
                if ty_prop.get('isReference'):
                    prop_type = f'cmof.Ref[{prop_type}]'
                if ty_prop.get('isMany'):
                    prop_type = f'List[{prop_type}]'
                ty_contains.add(prop_type)
        ty_contains = list(sorted(ty_contains))
        ty_contains_len = len(ty_contains)
        if ty_contains_len > 0:
            if ty_contains_len > 1:
                print(f'    _contents: Union[{", ".join(ty_contains)}]', **kws)
            else:
                print(f'    _contents: {ty_contains[0]}', **kws)
        namespace_metadata = {
            'prefix': namespace,
            'localName': local_name,
            'name': f'{namespace}:{local_name}'
        }
        print(f'    _ns={namespace_metadata}\n', **kws)
        defined_already.add(local_name)
    for prop_name, prop in sorted(property_map.items()):
        if prop['ns']['prefix'] == namespace:
            prop_cls_name = f'{prop_name[0].upper()}{prop_name[1:]}'
            prop_type = _get_python_identifier(
                prop['type'], namespace, defined_already)
            print(f'class {prop_cls_name}(cmof.Property):', **kws)
            print(f'    value: {prop_type}', **kws)
            if 'xml' in prop:
                print(f'    _xml={prop["xml"]}', **kws)
            print(f'    _ns={prop["ns"]}\n', **kws)
            defined_already.add(prop_cls_name)
    print(f'PACKAGE_METADATA = {pprint.pformat(cmof_json, compact=True)}\n',
          **kws)
    print('registry = cmof.Registry([', **kws)
    for name in sorted(defined_already):
        print(f'    {name},', **kws)
    print(f"], package_map = {{'{namespace}': PACKAGE_METADATA}})", **kws)
