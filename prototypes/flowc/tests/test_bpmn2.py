import os
import os.path
import importlib
import unittest

from .test_cmof import SPECS, roundtrip_bpmn, cmof
from .. import bpmn2


PATH = os.path.dirname(__file__)
SPEC_PATHS = [
    os.path.join(PATH, '..', 'bpmn2', f'{spec}.py') for spec in SPECS
]


class TestBPMN2(unittest.TestCase):
    def test_roundtrip(self):
        roundtrip_bpmn(self, bpmn2)


if __name__ == '__main__':
    unittest.main()
