import unittest
from unittest.mock import Mock, patch

import copy
import xmltodict

from collections import OrderedDict
from flowlib import bpmn

xml = \
'<?xml version="1.0" encoding="UTF-8"?>' \
'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" ' \
'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" ' \
'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" ' \
'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" ' \
'id="Definitions_0d4zc4f" targetNamespace="http://bpmn.io/schema/bpmn">' \
    '<bpmn:process id="Underpants" isExecutable="true">' \
        '<bpmn:startEvent id="StartEvent_1" name="Start">' \
            '<bpmn:outgoing>SequenceFlow_One</bpmn:outgoing>' \
        '</bpmn:startEvent>' \
        '<bpmn:sequenceFlow id="SequenceFlow_One" sourceRef="StartEvent_1" targetRef="Task_One" />' \
        '<bpmn:serviceTask id="Task_One" name="Collect underpants">' \
            '<bpmn:incoming>SequenceFlow_One</bpmn:incoming>' \
            '<bpmn:outgoing>SequenceFlow_Two</bpmn:outgoing>' \
        '</bpmn:serviceTask>' \
        '<bpmn:sequenceFlow id="SequenceFlow_Two" sourceRef="Task_One" targetRef="Task_Two" />' \
        '<bpmn:serviceTask id="Task_Two" name="Profit!">' \
            '<bpmn:incoming>SequenceFlow_Three</bpmn:incoming>' \
            '<bpmn:outgoing>SequenceFlow_Four</bpmn:outgoing>' \
            '</bpmn:serviceTask>' \
        '<bpmn:endEvent id="EndEvent_One" name="Finish">' \
            '<bpmn:incoming>SequenceFlow_Four</bpmn:incoming>' \
        '</bpmn:endEvent>' \
        '<bpmn:sequenceFlow id="SequenceFlow_Four" sourceRef="Task_Two" targetRef="EndEvent_One" />' \
        '<bpmn:serviceTask id="Task_Two" name="Dot dot dot...">' \
            '<bpmn:incoming>SequenceFlow_Two</bpmn:incoming>' \
            '<bpmn:outgoing>SequenceFlow_Three</bpmn:outgoing>' \
        '</bpmn:serviceTask>' \
        '<bpmn:sequenceFlow id="SequenceFlow_Three" sourceRef="Task_Two" targetRef="Task_Two" />' \
        '<bpmn:textAnnotation id="TextAnnotation_One">' \
            '<bpmn:text>rexflow:\n' \
            '    orchestrator: docker</bpmn:text>' \
        '</bpmn:textAnnotation>' \
        '<bpmn:association id="Association_One" sourceRef="StartEvent_1" targetRef="TextAnnotation_One" />' \
        '<bpmn:textAnnotation id="TextAnnotation_Two">' \
            '<bpmn:text>rexflow:\n' \
            '    preexisting: false\n' \
            '    service:\n' \
            '        host: localhost\n' \
            '        port: 5000</bpmn:text>' \
        '</bpmn:textAnnotation>' \
        '<bpmn:association id="Association_Two" sourceRef="Task_One" targetRef="TextAnnotation_Two" />' \
        '<bpmn:textAnnotation id="TextAnnotation_Three">' \
            '<bpmn:text>rexflow:\n' \
            '    service:\n' \
            '        host: localhost\n' \
            '        port: 5002</bpmn:text>' \
        '</bpmn:textAnnotation>' \
        '<bpmn:association id="Association_Three" sourceRef="Task_Two" targetRef="TextAnnotation_Three" />' \
        '<bpmn:textAnnotation id="TextAnnotation_Four">' \
            '<bpmn:text>rexflow:\n' \
            '    service:\n' \
            '        host: localhost\n' \
            '        port: 5004</bpmn:text>' \
        '</bpmn:textAnnotation>' \
        '<bpmn:association id="Association_Four" sourceRef="Task_Two" targetRef="TextAnnotation_Four" />' \
    '</bpmn:process>' \
'</bpmn:definitions>'

        # '<bpmn:intermediateThrowEvent id="Event_Zero">' \
        #     '<bpmn:incoming>Flow_Zero</bpmn:incoming>' \
        # '</bpmn:intermediateThrowEvent>' \
        # '<bpmn:intermediateThrowEvent id="Event_One">' \
        #     '<bpmn:outgoing>Flow_One</bpmn:outgoing>' \
        # '</bpmn:intermediateThrowEvent>' \


class TestBpmnProcess(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls._xml = xmltodict.parse(xml)
        cls._definition = cls._xml['bpmn:definitions']
        cls._process = cls._definition['bpmn:process']

    def test_init(self):
        out = bpmn.BPMNProcess(self._xml)



if __name__ == '__main__':
    unittest.main()
