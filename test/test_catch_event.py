from flowlib.bpmn_util import WorkflowProperties
import unittest
from unittest.mock import Mock, patch

import copy
import xmltodict

from collections import OrderedDict
from flowlib import catch_event

xml = \
'<?xml version="1.0" encoding="UTF-8"?>' \
'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"' \
' xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"' \
' xmlns:di="http://www.omg.org/spec/DD/20100524/DI"' \
' id="Definitions_One"' \
' targetNamespace="http://bpmn.io/schema/bpmn">' \
'<bpmn:process id="Underpants" isExecutable="true">' \
    '<bpmn:startEvent id="StartEvent_1" name="Start">' \
      '<bpmn:outgoing>SequenceFlow_190n0mt</bpmn:outgoing>' \
    '</bpmn:startEvent>' \
    '<bpmn:sequenceFlow id="SequenceFlow_190n0mt" sourceRef="StartEvent_1" targetRef="Task_1dqvybv" />' \
    '<bpmn:serviceTask id="Task_1dqvybv" name="Collect underpants">' \
      '<bpmn:incoming>SequenceFlow_190n0mt</bpmn:incoming>' \
      '<bpmn:outgoing>Flow_0sgm8j8</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:serviceTask id="Task_1mrtiy4" name="Profit!">' \
      '<bpmn:incoming>Flow_0pyd3vm</bpmn:incoming>' \
      '<bpmn:outgoing>SequenceFlow_16qxrei</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:endEvent id="EndEvent_1pxdd1k" name="Finish">' \
      '<bpmn:incoming>SequenceFlow_16qxrei</bpmn:incoming>' \
    '</bpmn:endEvent>' \
    '<bpmn:sequenceFlow id="SequenceFlow_16qxrei" sourceRef="Task_1mrtiy4" targetRef="EndEvent_1pxdd1k" />' \
    '<bpmn:intermediateThrowEvent id="Event_1cptoky">' \
      '<bpmn:incoming>Flow_0sgm8j8</bpmn:incoming>' \
    '</bpmn:intermediateThrowEvent>' \
    '<bpmn:sequenceFlow id="Flow_0sgm8j8" sourceRef="Task_1dqvybv" targetRef="Event_1cptoky" />' \
    '<bpmn:sequenceFlow id="Flow_0pyd3vm" sourceRef="Activity_0bekv98" targetRef="Task_1mrtiy4" />' \
    '<bpmn:sequenceFlow id="Flow_09ozihg" sourceRef="Event_0w7y6jt" targetRef="Activity_0bekv98" />' \
    '<bpmn:serviceTask id="Activity_0bekv98" name="Sauce">' \
      '<bpmn:incoming>Flow_09ozihg</bpmn:incoming>' \
      '<bpmn:outgoing>Flow_0pyd3vm</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:intermediateCatchEvent id="Event_0w7y6jt">' \
      '<bpmn:outgoing>Flow_09ozihg</bpmn:outgoing>' \
      '<bpmn:messageEventDefinition id="MessageEventDefinition_0zfzgj3" />' \
    '</bpmn:intermediateCatchEvent>' \
    '<bpmn:textAnnotation id="TextAnnotation_0awc0mf">' \
      '<bpmn:text>rexflow:\n' \
'    id: events</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_0hwix5o" sourceRef="StartEvent_1" targetRef="TextAnnotation_0awc0mf" />' \
    '<bpmn:textAnnotation id="TextAnnotation_1vjflrc">' \
      '<bpmn:text>rexflow:\n' \
'    service:\n' \
'        host: collect\n' \
'        port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_1uohovd" sourceRef="Task_1dqvybv" targetRef="TextAnnotation_1vjflrc" />' \
    '<bpmn:textAnnotation id="TextAnnotation_18mql5m">' \
      '<bpmn:text>rexflow:\n' \
'    service:\n' \
'        host: profit\n' \
'        port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_1yz0l60" sourceRef="Task_1mrtiy4" targetRef="TextAnnotation_18mql5m" />' \
    '<bpmn:textAnnotation id="TextAnnotation_06yt33r">' \
      '<bpmn:text>rexflow:\n' \
'  queue: mytopic\n' \
'  gateway_name: stolenpants</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_057this" sourceRef="Event_1cptoky" targetRef="TextAnnotation_06yt33r" />' \
    '<bpmn:textAnnotation id="TextAnnotation_0dqtqab">' \
      '<bpmn:text>rexflow:\n' \
'  queue: mytopic\n' \
'  gateway_name: saucedpants</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:textAnnotation id="TextAnnotation_02eute1">' \
      '<bpmn:text>rexflow:\n' \
'  service:\n' \
'    host: secret-sauce\n' \
'    port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_189jawh" sourceRef="Activity_0bekv98" targetRef="TextAnnotation_02eute1" />' \
    '<bpmn:association id="Association_0ahotq6" sourceRef="Event_0w7y6jt" targetRef="TextAnnotation_0dqtqab" />' \
    '<bpmn:textAnnotation id="TextAnnotation_1ov6vvr">' \
      '<bpmn:text>rexflow:\n' \
'  service:\n' \
'    host: end-events</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_0xfwgko" sourceRef="EndEvent_1pxdd1k" targetRef="TextAnnotation_1ov6vvr" />' \
  '</bpmn:process>' \
'</bpmn:definitions>'

class TestBpmnCatchEvent(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls._xml = xmltodict.parse(xml)
        cls._definition = cls._xml['bpmn:definitions']
        cls._process = cls._definition['bpmn:process']
        print(cls._process)

    def test_init(self):
        event = self._process['bpmn:intermediateCatchEvent']
        out = catch_event.BPMNCatchEvent(event, self._process, WorkflowProperties())


if __name__ == '__main__':
    unittest.main()
