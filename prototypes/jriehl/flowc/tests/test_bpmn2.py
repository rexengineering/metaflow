import os, os.path
import importlib
import unittest

from .test_cmof import SPECS, roundtrip_bpmn


PATH = os.path.dirname(__file__)
SPEC_PATHS = [
    os.path.join(PATH, '..', 'bpmn2', f'{spec}.py') for spec in SPECS
]


class TestBPMN2(unittest.TestCase):
    @property
    def bpmn2(self):
        if not hasattr(self, '_bpmn2'):
            self._bpmn2 = importlib.import_module('.bpmn2', 'flowc')
        return self._bpmn2

    def test_dynamic_import(self):
        for spec_path in SPEC_PATHS:
            if os.path.exists(spec_path):
                os.unlink(spec_path)
        self._bpmn2 = importlib.import_module('.bpmn2', 'flowc')

    def test_roundtrip(self):
        roundtrip_bpmn(self, self.bpmn2)


if __name__ == '__main__':
    unittest.main()
