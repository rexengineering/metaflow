import os
import os.path
import importlib
import unittest

from .test_cmof import SPECS, roundtrip_bpmn, cmof


PATH = os.path.dirname(__file__)
SPEC_PATHS = [
    os.path.join(PATH, '..', 'bpmn2', f'{spec}.py') for spec in SPECS
]


class TestBPMN2(unittest.TestCase):
    _bpmn2: cmof.CMOFModule

    def _dynamic_import(self) -> cmof.CMOFModule:
        '''Isolates "illegal" downcast from types.ModuleType to
        cmof.CMOFModule.
        '''
        return importlib.import_module(
            '.bpmn2', 'prototypes.jriehl.flowc'
        )

    @property
    def bpmn2(self) -> cmof.CMOFModule:
        if not hasattr(self, '_bpmn2'):
            self._bpmn2 = self._dynamic_import()
        return self._bpmn2

    def test_dynamic_import(self):
        for spec_path in SPEC_PATHS:
            if os.path.exists(spec_path):
                os.unlink(spec_path)
        self._bpmn2 = self._dynamic_import()

    def test_roundtrip(self):
        roundtrip_bpmn(self, self.bpmn2)


if __name__ == '__main__':
    unittest.main()
