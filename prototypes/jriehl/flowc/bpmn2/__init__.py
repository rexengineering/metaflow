SPECS = 'dc', 'di', 'bioc', 'bpmndi', 'bpmn'

__all__ = list(SPECS) + ['registry']


import importlib
import json
import os.path

from .. import cmof


PATH = os.path.dirname(__file__)


def _try_import_else_codegen(spec_name):
    module_globals = globals()
    try:
        result = importlib.import_module(f'.{spec_name}', __name__)
    except ImportError:
        spec_json_path = os.path.join(PATH, '..', 'data', f'{spec_name}.json')
        with open(spec_json_path) as file_obj:
            spec_dict = json.load(file_obj)
        module_path = os.path.join(PATH, f'{spec_name}.py')
        with open(module_path, 'w') as file_obj:
            cmof.code_gen(
                spec_dict, spec_name, file=file_obj, cmof_package='..'
            )
        result = importlib.import_module(f'.{spec_name}', __name__)
    module_globals[spec_name] = result
    return result


registry = cmof.Registry()

for spec_name in SPECS:
    spec_module = _try_import_else_codegen(spec_name)
    registry.update(spec_module.registry)
