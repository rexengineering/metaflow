import unittest
from unittest.mock import Mock, patch

from test_bpmn_util import xml
import copy
import xmltodict
from collections import OrderedDict
from bpmn import BPMNProcess

class TestBpmnProcess(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls._xml = xmltodict.parse(xml)
        cls._definition = cls._xml['bpmn:definitions']
        cls._process = cls._definition['bpmn:process']

    def test_init(self):
        out = BPMNProcess(self._xml)



if __name__ == '__main__':
    unittest.main()
