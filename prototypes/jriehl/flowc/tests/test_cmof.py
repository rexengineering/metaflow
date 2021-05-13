# pyright:
import importlib.util
import json
import os.path
import sys
import tempfile
import types
import unittest

from .. import cmof

SPECS = 'dc', 'di', 'bioc', 'bpmndi', 'bpmn'
PATH = os.path.dirname(__file__)


def get_module(module_name: str, module_path: str) -> types.ModuleType:
    '''Load a Python module from a given file path.

    Module import mechanism courtesy of:
    https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
    '''
    module_spec = importlib.util.spec_from_file_location(
        module_name, module_path)
    module = importlib.util.module_from_spec(module_spec)
    exec_module = getattr(module_spec.loader, 'exec_module')
    exec_module(module)
    return module


def get_bpmn_metamodel() -> cmof.CMOFModule:
    '''Generate and load the BPMN metamodel, and all its dependencies.
    '''
    spec_modules = {}
    TEMPDIR = tempfile.gettempdir()
    if TEMPDIR not in sys.path:
        sys.path.append(TEMPDIR)
    for spec_name in SPECS:
        spec_json_path = os.path.join(PATH, '..', 'data', f'{spec_name}.json')
        with open(spec_json_path) as fileobj:
            spec_dict = json.load(fileobj)
        module_path = os.path.join(TEMPDIR, f'{spec_name}.py')
        with open(module_path, 'w') as fileobj:
            cmof.code_gen(
                spec_dict, spec_name, file=fileobj,
                cmof_package='prototypes.jriehl.flowc'
            )
        spec_modules[spec_name] = get_module(spec_name, module_path)
    bpmn = spec_modules['bpmn']
    for dependency in spec_modules.values():
        if dependency.__name__ != 'bpmn':
            bpmn.registry.update(dependency.registry)
    sys.path.remove(TEMPDIR)
    return bpmn


def roundtrip_bpmn(tester: unittest.TestCase, bpmn: cmof.CMOFModule):
    example_path = os.path.join(
        PATH, '..', '..', '..', '..', 'examples/underpants/underpants.bpmn')
    with open(example_path) as fileobj:
        example_src = fileobj.read()
    underpants1 = bpmn.registry.from_xml(example_src)  # type: cmof.Element
    xml1 = underpants1.to_xml(pretty=True, short_empty_elements=True)
    assert xml1 is not None
    if __debug__:
        print(xml1)
    underpants2 = bpmn.registry.from_xml(xml1)  # type: cmof.Element
    xml2 = underpants2.to_xml(pretty=True, short_empty_elements=True)
    if __debug__:
        print(xml2)
    tester.assertEqual(xml1, xml2)


class TestCMOF(unittest.TestCase):
    def test_round_trip(self):
        bpmn = get_bpmn_metamodel()
        roundtrip_bpmn(self, bpmn)


if __name__ == '__main__':
    unittest.main()
