import unittest
from unittest.mock import Mock, patch

import copy
import xmltodict

from collections import OrderedDict
from flowlib import bpmn

xml = \
'<?xml version="1.0" encoding="UTF-8"?>' \
'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"' \
' xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"' \
' xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"' \
' xmlns:di="http://www.omg.org/spec/DD/20100524/DI"' \
' id="Definitions_One"' \
' targetNamespace="http://bpmn.io/schema/bpmn" exporter="Zeebe Modeler" exporterVersion="0.10.0">' \
  '<bpmn:process id="Underpants" isExecutable="true">' \
    '<bpmn:startEvent id="StartEvent_One" name="Start">' \
      '<bpmn:outgoing>SequenceFlow_One</bpmn:outgoing>' \
    '</bpmn:startEvent>' \
    '<bpmn:sequenceFlow id="SequenceFlow_One" sourceRef="StartEvent_One" targetRef="Task_One" />' \
    '<bpmn:serviceTask id="Task_One" name="Collect underpants">' \
      '<bpmn:extensionElements>' \
        '<zeebe:taskDefinition type="collect" />' \
      '</bpmn:extensionElements>' \
      '<bpmn:incoming>SequenceFlow_One</bpmn:incoming>' \
      '<bpmn:outgoing>SequenceFlow_Two</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:sequenceFlow id="SequenceFlow_Two" sourceRef="Task_One" targetRef="Task_Two" />' \
    '<bpmn:serviceTask id="Task_Three" name="Profit!">' \
      '<bpmn:extensionElements>' \
        '<zeebe:taskDefinition type="profit" />' \
      '</bpmn:extensionElements>' \
      '<bpmn:incoming>SequenceFlow_Three</bpmn:incoming>' \
      '<bpmn:outgoing>SequenceFlow_Four</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:endEvent id="EndEvent_One" name="Finish">' \
      '<bpmn:incoming>SequenceFlow_Four</bpmn:incoming>' \
    '</bpmn:endEvent>' \
    '<bpmn:sequenceFlow id="SequenceFlow_Four" sourceRef="Task_Three" targetRef="EndEvent_One" />' \
    '<bpmn:serviceTask id="Task_Two" name="Dot dot dot...">' \
      '<bpmn:extensionElements>' \
        '<zeebe:taskDefinition type="secret-sauce" />' \
      '</bpmn:extensionElements>' \
      '<bpmn:incoming>SequenceFlow_Two</bpmn:incoming>' \
      '<bpmn:outgoing>SequenceFlow_Three</bpmn:outgoing>' \
    '</bpmn:serviceTask>' \
    '<bpmn:sequenceFlow id="SequenceFlow_Three" sourceRef="Task_Two" targetRef="Task_Three" />' \
    '<bpmn:textAnnotation id="TextAnnotation_One">' \
      '<bpmn:text>rexflow:\n' \
'    id: underpants\n' \
'    namespace: default\n' \
'    namespace_shared: true</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_One" sourceRef="StartEvent_One" targetRef="TextAnnotation_One" />' \
    '<bpmn:textAnnotation id="TextAnnotation_Two">' \
      '<bpmn:text>rexflow:\n' \
'    service:\n' \
'        host: collect\n' \
'        port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_Two" sourceRef="Task_One" targetRef="TextAnnotation_Two" />' \
    '<bpmn:textAnnotation id="TextAnnotation_Three">' \
      '<bpmn:text>rexflow:\n' \
'    service:\n' \
'        host: secret-sauce\n' \
'        port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_Three" sourceRef="Task_Two" targetRef="TextAnnotation_Three" />' \
    '<bpmn:textAnnotation id="TextAnnotation_Four">' \
      '<bpmn:text>rexflow:\n' \
'    service:\n' \
'        host: profit\n' \
'        port: 5000</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_Four" sourceRef="Task_Three" targetRef="TextAnnotation_Four" />' \
    '<bpmn:textAnnotation id="TextAnnotation_Five">' \
      '<bpmn:text>rexflow:\n' \
'  service:\n' \
'    host: gnomes</bpmn:text>' \
    '</bpmn:textAnnotation>' \
    '<bpmn:association id="Association_Five" sourceRef="EndEvent_One" targetRef="TextAnnotation_Five" />' \
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
        ''' Normal BPMNProcess init
        '''
        out = bpmn.BPMNProcess(self._process)
        self.assertEqual(len(out.tasks),3)
        self.assertEqual(len(out.kafka_topics),0)
        self.assertEqual(len(out.xgateways),0)
        self.assertEqual(len(out.end_events),1)
        self.assertEqual(len(out.throws),0)
        self.assertEqual(len(out.catches),0)
        self.assertEqual(len(out.component_map),5)
        self.assertEqual(len(out.all_components),3)

    def test_init_no_startevent_raises(self):
        ''' BPMNProcess init with no startEvent - should raise KeyError
        '''
        tmp = copy.deepcopy(self._process)
        tmp.pop('bpmn:startEvent')
        with self.assertRaises(KeyError):
            out = bpmn.BPMNProcess(tmp)

    def test_init_multi_startevent_raises(self):
        ''' BPMNProcess init with two startEvent - should raise AssertionError
        '''
        tmp = copy.deepcopy(self._process)
        tmp['bpmn:startEvent'] = ['one','two']
        with self.assertRaises(AssertionError):
            out = bpmn.BPMNProcess(tmp)

    def test_init_multi_startevent_annotation_raises(self):
        ''' BPMNProcess init with two startEvent annotations - should raise AssertionError
        '''
        tmp = copy.deepcopy(self._process)
        tmp['bpmn:textAnnotation'].append(copy.deepcopy(tmp['bpmn:textAnnotation'][0]))
        with self.assertRaises(AssertionError):
            out = bpmn.BPMNProcess(tmp)

    def test_init_no_workflow_id_raises(self):
        ''' BPMNProcess init with no workflow id - should raise AssertionError
        '''
        tmp = copy.deepcopy(self._process)
        x = tmp['bpmn:textAnnotation'][0]['bpmn:text'].replace('\xa0 \xa0 id: underpants\n','')
        tmp['bpmn:textAnnotation'][0]['bpmn:text'] = x
        with self.assertRaises(AssertionError):
            out = bpmn.BPMNProcess(tmp)

    def test_to_kubernetes_raies(self):
        ''' BPMNProcess.to_kubernetes - should raise NotImplementedError
        '''
        out = bpmn.BPMNProcess(self._process)
        with self.assertRaises(NotImplementedError):
            out.to_kubernetes()

    # not sure how to test to_istio, but it should be tested since we rely on it so much.
    def test_to_istio(self):
        ''' BPMNProcess.to_istio - test not implemented
        '''
        pass

if __name__ == '__main__':
    unittest.main()
