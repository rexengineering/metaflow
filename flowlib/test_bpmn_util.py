import unittest
from unittest.mock import Mock, patch

import bpmn_util
import copy
import xmltodict
from collections import OrderedDict


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

class TestBpmnUtil(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._xml = xmltodict.parse(xml)
        cls._definition = cls._xml['bpmn:definitions']
        cls._process = cls._definition['bpmn:process']

    def test_iter_xmldict_for_key_one(self):
        ''' iter_xmldict_for_key returns only a single match
        '''
        result = None
        d = OrderedDict([('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)])
        c = 0
        for r in bpmn_util.iter_xmldict_for_key(d, 'three'):
            c = c + 1
        self.assertEqual(1,c)

    def test_iter_xmldict_for_key_list(self):
        ''' iter_xmldict_for_key iterates through list
        '''
        d = OrderedDict([('hello', 'world'), ('world', ['one','two','three','four','five'])])
        c = 0
        for r in bpmn_util.iter_xmldict_for_key(d, 'world'):
            c = c + 1
        self.assertEqual(c, 5)

    def test_raw_proc_to_digraph(self):
        ''' raw_proc_to_digraph returns expected digraph
        '''
        self.assertIsNotNone(self._process)
        digraph = bpmn_util.raw_proc_to_digraph(self._process)
        self.assertEqual(len(digraph.keys()), 3)
        self.assertListEqual(list(digraph), ['StartEvent_1', 'Task_One', 'Task_Two'])
        self.assertListEqual(list(digraph.values()), [{'Task_One'}, {'Task_Two'}, {'EndEvent_One', 'Task_Two'}])

    def test_get_annotations_no_source_ref(self):
        ''' get_annotations with no source_ref
        '''
        self.assertIsNotNone(self._process)
        annotations = list(bpmn_util.get_annotations(self._process))
        self.assertEqual(len(annotations),4)

    def test_get_annotations_with_source_ref(self):
        ''' get_annotations with with source_ref 'Task_One'
        '''
        self.assertIsNotNone(self._process)
        annotations = list(bpmn_util.get_annotations(self._process, 'Task_One'))
        self.assertEqual(len(annotations),1)

    def test_parse_events_no_results(self):
        ''' parse_events no results
        '''
        results = bpmn_util.parse_events(self._process)
        self.assertEqual(len(results['throw']),0)
        self.assertEqual(len(results['catch']),0)

    def test_parse_events_one_throw(self):
        ''' parse_events one throw
        '''
        eve = []
        eve.append(OrderedDict({('@id','catch_event_0'),('bpmn:incoming','Flow_0')}))
        oth = copy.deepcopy(self._process)
        oth['bpmn:intermediateThrowEvent'] = eve
        results = bpmn_util.parse_events(oth)
        self.assertEqual(len(results['throw']),1)
        self.assertEqual(len(results['catch']),0)
    
    def test_parse_events_one_catch(self):
        ''' parse_events one catch
        '''
        eve = []
        eve.append(OrderedDict({('@id','throw_event_0'),('bpmn:outgoing','Flow_1')}))
        oth = copy.deepcopy(self._process)
        oth['bpmn:intermediateThrowEvent'] = eve
        results = bpmn_util.parse_events(oth)
        self.assertEqual(len(results['throw']),0)
        self.assertEqual(len(results['catch']),1)

    def test_parse_events_one_throw_catch(self):
        ''' parse_events one catch
        '''
        eve = []
        eve.append(OrderedDict({('@id','catch_event_0'),('bpmn:incoming','Flow_0')}))
        eve.append(OrderedDict({('@id','throw_event_0'),('bpmn:outgoing','Flow_1')}))
        oth = copy.deepcopy(self._process)
        oth['bpmn:intermediateThrowEvent'] = eve
        results = bpmn_util.parse_events(oth)
        self.assertEqual(len(results['throw']),1)
        self.assertEqual(len(results['catch']),1)

#
# ServiceProperties tests
#
class TestServiceProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = 'host_name'
        cls.host_xlate = 'host-name'
        cls.port = 1234
        cls.protocol = 'proto_col'
        cls.container = 'con_tainer'
        cls.id_hash = 'id_hash'
        cls.namespace = 'name_space'
        cls.full_host = f'{cls.host_xlate}-{cls.id_hash}'

    def test_init_no_annotations(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.ServiceProperties()
        self.assertIsNone(out._host)
        self.assertIsNone(out._port)
        self.assertIsNone(out._protocol)
        self.assertIsNone(out._container_name)
        self.assertIsNone(out._id_hash)
        self.assertFalse(out._is_hash_used)
        self.assertIsNone(out._namespace)
        return out

    def test_init_host_and_port(self):
        ''' Create with host and port
        '''
        out = bpmn_util.ServiceProperties({'host': self.host, 'port': str(self.port)})
        self.assertEqual(out.host, self.host_xlate)
        self.assertEqual(out.port, self.port)  # converted to scaler
        self.assertIsNone(out._protocol)
        self.assertEqual(out._container_name, self.host) # update host also updates container name
        self.assertIsNone(out._id_hash)
        self.assertFalse(out._is_hash_used)
        self.assertIsNone(out._namespace)

    def test_update_protocol(self):
        ''' Create with protocol annotation
        '''
        out = self.test_init_no_annotations()
        out.update({'protocol':self.protocol})
        self.assertIsNone(out._host)
        self.assertIsNone(out._port)
        self.assertEqual(out._protocol, self.protocol)
        self.assertIsNone(out._container_name)
        self.assertIsNone(out._id_hash)
        self.assertFalse(out._is_hash_used)
        self.assertIsNone(out._namespace)

    def test_update_container_name(self):
        ''' Create with container annotation
        '''
        out = self.test_init_no_annotations()
        out.update({'container':self.container})
        self.assertIsNone(out._host)
        self.assertIsNone(out._port)
        self.assertIsNone(out._protocol)
        self.assertEqual(out.container, self.container)
        self.assertIsNone(out._id_hash)
        self.assertFalse(out._is_hash_used)
        self.assertIsNone(out._namespace)

    def test_update_id_hash(self):
        ''' id_hash is used with the host name when _is_hash_used is True
        '''
        out = self.test_init_no_annotations()
        out.update({'host':self.host, 'port':self.port, 'hash_used':True, 'id_hash':self.id_hash})
        self.assertEqual(out.host, self.full_host)
        self.assertEqual(out.port, self.port)
        self.assertIsNone(out._protocol)
        self.assertEqual(out.container, self.host)
        self.assertEqual(out._id_hash, self.id_hash)
        self.assertTrue(out._is_hash_used)
        self.assertIsNone(out._namespace)

    # def test_update_id_namespace(self):
    #     ''' namespace cannot be set and is not used.
    #     '''
    #     out = self.test_init_no_annotations()
    #     out.update({'namespace':self.namespace})
    #     self.assertIsNone(out._host)
    #     self.assertIsNone(out._port)
    #     self.assertIsNone(out._protocol)
    #     self.assertIsNone(out._container_name)
    #     self.assertIsNone(out._id_hash)
    #     self.assertFalse(out._is_hash_used)
    #     self.assertEqual(out.namespace, self.namespace)

#
# CallProperties tests
#
class TestCallProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = 'this-is-a-path'
        cls.method = 'this-is-a-method'
        cls.serialization = 'this-is-a-serialization'
        cls.total_attempts = 999

    def test_init_no_annotations(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.CallProperties()
        self.assertIsNone(out._path)
        self.assertEqual(out.path,'/')
        self.assertIsNone(out._method)
        self.assertEqual(out.method,'POST')
        self.assertIsNone(out._serialization)
        self.assertEqual(out.serialization,'JSON')
        self.assertIsNone(out._total_attempts)
        self.assertEqual(out.total_attempts,2)

    def test_init_path(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.CallProperties()
        out.update({'path':self.path})
        self.assertEqual(out.path, self.path)
        self.assertIsNone(out._method)
        self.assertIsNone(out._serialization)
        self.assertIsNone(out._total_attempts)

    def test_init_method(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.CallProperties()
        out.update({'method':self.method})
        self.assertIsNone(out._path)
        self.assertEqual(out.method,self.method)
        self.assertIsNone(out._serialization)
        self.assertIsNone(out._total_attempts)

    def test_init_serialization(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.CallProperties()
        out.update({'serialization':self.serialization})
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertEqual(out.serialization,self.serialization)
        self.assertIsNone(out._total_attempts)

    def test_init_total_attempts(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.CallProperties()
        out.update({'retry':{'total_attempts':self.total_attempts}})
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertIsNone(out._serialization)
        self.assertEqual(out.total_attempts,self.total_attempts)

#
# HealthProperties tests
#
class TestHealthProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = 'this-is-a-path'
        cls.method = 'this-is-a-method'
        cls.query = 'this-is-a-query'
        cls.period = 999
        cls.response = 'this-is-a-response'

    def test_init_no_annotations(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertIsNone(out.query)
        self.assertIsNone(out._period)
        self.assertIsNone(out._response)

        self.assertEqual(out.path,'/')
        self.assertEqual(out.method,'GET')
        self.assertEqual(out.period,30)
        self.assertEqual(out.response,'HEALTHY')

    def test_init_path(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        out.update({'path':self.path})
        self.assertEqual(out.path, self.path)
        self.assertIsNone(out._method)
        self.assertIsNone(out.query)
        self.assertIsNone(out._period)
        self.assertIsNone(out._response)

        self.assertEqual(out.method,'GET')
        self.assertEqual(out.period,30)
        self.assertEqual(out.response,'HEALTHY')

    def test_init_method(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        out.update({'method':self.method})
        self.assertIsNone(out._path)
        self.assertEqual(out.method, self.method)
        self.assertIsNone(out.query)
        self.assertIsNone(out._period)
        self.assertIsNone(out._response)

        self.assertEqual(out.path,'/')
        self.assertEqual(out.period,30)
        self.assertEqual(out.response,'HEALTHY')

    def test_init_query(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        out.update({'query':self.query})
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertEqual(out.query, self.query)
        self.assertIsNone(out._period)
        self.assertIsNone(out._response)

        self.assertEqual(out.path,'/')
        self.assertEqual(out.method,'GET')
        self.assertEqual(out.period,30)
        self.assertEqual(out.response,'HEALTHY')

    def test_init_period(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        out.update({'period':self.period})
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertIsNone(out.query)
        self.assertEqual(out.period,self.period)
        self.assertIsNone(out._response)

        self.assertEqual(out.path,'/')
        self.assertEqual(out.method,'GET')
        self.assertEqual(out.response,'HEALTHY')

    def test_init_response(self):
        ''' Create object without any annotations (empty object)
        '''
        out = bpmn_util.HealthProperties()
        out.update({'response':self.response})
        self.assertIsNone(out._path)
        self.assertIsNone(out._method)
        self.assertIsNone(out.query)
        self.assertIsNone(out._period)
        self.assertEqual(out.response,self.response)

        self.assertEqual(out.path,'/')
        self.assertEqual(out.method,'GET')
        self.assertEqual(out.period,30)

#
# WorkflowProperties tests
#

class TestWorkflowProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orchestrator = 'this-is-orchestrator'  # default to istio...
        cls.id = 'this-is-an-id'
        cls.namespace = 'this-is-a-namespace'
        cls.namespace_shared = True
        cls.id_hash = bpmn_util.calculate_id_hash(cls.id)
        cls.retry_total_attempts = 999
        cls.is_recoverable = True
        # if annotations is not None:
        #     if 'rexflow' in annotations:
        #         self.update(annotations['rexflow'])

    def test_init_no_annotations(self):
        ''' Create WorkflowProperties without any annotations (empty object)
        '''
        out = bpmn_util.WorkflowProperties()
        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,'')
        self.assertEqual(out.namespace,'default')
        self.assertFalse(out.namespace_shared)
        self.assertEqual(out.id_hash,'')
        self.assertEqual(out.retry_total_attempts,2)
        self.assertFalse(out.is_recoverable)

    def test_init_orchestrator(self):
        ''' Create WorkflowProperties with orchestrator annotation - raises
        '''
        out = bpmn_util.WorkflowProperties()
        with self.assertRaises(AssertionError):
            out.update({'orchestrator':self.orchestrator})

    def test_init_id(self):
        ''' Create WorkflowProperties with id annotation 
        '''
        out = bpmn_util.WorkflowProperties()
        out.update({'id':self.id})

        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,self.id)
        self.assertEqual(out.namespace,self.id)
        self.assertFalse(out.namespace_shared)
        self.assertEqual(out.id_hash,self.id_hash)
        self.assertEqual(out.retry_total_attempts,2)
        self.assertFalse(out.is_recoverable)

    def test_init_namespace_shared(self):
        ''' Create WorkflowProperties with namespace_shared annotation 
        '''
        out = bpmn_util.WorkflowProperties()
        out.update({'namespace_shared':self.namespace_shared})

        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,'')
        self.assertEqual(out.namespace,'default')
        self.assertEqual(out.namespace_shared, self.namespace_shared)
        self.assertEqual(out.id_hash,'')
        self.assertEqual(out.retry_total_attempts,2)
        self.assertFalse(out.is_recoverable)

    def test_init_namespace_raises(self):
        ''' Create WorkflowProperties with namespace annotation without setting
            'shared' first
        '''
        out = bpmn_util.WorkflowProperties()
        with self.assertRaises(AssertionError):
            out.update({'namespace':self.namespace})

    def test_init_namespace(self):
        ''' Create WorkflowProperties with namespace annotation 
        '''
        out = bpmn_util.WorkflowProperties()
        out.update({'namespace':self.namespace, 'namespace_shared':True})

        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,'')
        self.assertEqual(out.namespace, self.namespace)
        self.assertTrue(out.namespace_shared)
        self.assertEqual(out.id_hash,'')
        self.assertEqual(out.retry_total_attempts,2)
        self.assertFalse(out.is_recoverable)

    def test_init_recoverable(self):
        ''' Create WorkflowProperties with recoverable annotation 
        '''
        out = bpmn_util.WorkflowProperties()
        out.update({'recoverable':self.is_recoverable})

        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,'')
        self.assertEqual(out.namespace, 'default')
        self.assertFalse(out.namespace_shared)
        self.assertEqual(out.id_hash,'')
        self.assertEqual(out.retry_total_attempts,2)
        self.assertEqual(out.is_recoverable,self.is_recoverable)

    def test_init_retry_total_attempts(self):
        ''' Create WorkflowProperties with retry_total_attempts annotation 
        '''
        out = bpmn_util.WorkflowProperties()
        out.update({'retry':{'total_attempts':self.retry_total_attempts}})

        self.assertEqual(out.orchestrator,'istio')
        self.assertEqual(out.id,'')
        self.assertEqual(out.namespace, 'default')
        self.assertFalse(out.namespace_shared)
        self.assertEqual(out.id_hash,'')
        self.assertEqual(out.retry_total_attempts,self.retry_total_attempts)
        self.assertFalse(out.is_recoverable,self.is_recoverable)

#
# BPMNComponent tests
#
class TestBPMNComponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._xml = xmltodict.parse(xml)
        cls._definition = cls._xml['bpmn:definitions']
        cls._process = cls._definition['bpmn:process']
        cls._wfprops = bpmn_util.WorkflowProperties()


    def test_init_no_rexflow_annot_raises(self):
        ''' Init BPMNComponent providing multiple rexflow annotations - should raise AssertionError
        '''
        with self.assertRaises(AssertionError):
            out = bpmn_util.BPMNComponent({'@id':'bad-id'}, self._process, bpmn_util.WorkflowProperties())

    def test_init(self):
        ''' Init BPMNComponent
        '''
        out = bpmn_util.BPMNComponent({'@id':'Task_One'}, self._process, self._wfprops)
        self.assertFalse(out.is_preexisting)
        self.assertEqual(out.is_in_shared_ns, self._wfprops.namespace_shared)
        self.assertEqual(out.namespace, self._wfprops.namespace)
        self.assertEqual(out._proc, self._process)
        self.assertFalse(out._service_properties._is_hash_used)
        self.assertEqual(out._service_properties._id_hash, '')

        self.assertEqual(out.namespace, self._wfprops.namespace)
        self.assertEqual(out.is_in_shared_ns, self._wfprops.namespace_shared)
        self.assertEqual(out.k8s_url, 'http://localhost.default:5000/')
        self.assertEqual(out.envoy_host, 'localhost.default.svc.cluster.local')
        self.assertEqual(out.annotation, {'preexisting': False, 'service': {'host': 'localhost', 'port': 5000}})
        self.assertEqual(out.path, '/')

    def test_init_with_preexisting(self):
        ''' init with annotation with prexisting true specified
        '''
        wrk = copy.deepcopy(self._process)
        wrk['bpmn:textAnnotation'][1]['bpmn:text'] = wrk['bpmn:textAnnotation'][1]['bpmn:text'].replace('false','true')

        out = bpmn_util.BPMNComponent({'@id':'Task_One'}, wrk, self._wfprops)
        self.assertTrue(out.is_preexisting)
        self.assertEqual(out.is_in_shared_ns, self._wfprops.namespace_shared)
        self.assertEqual(out.namespace, self._wfprops.namespace)
        self.assertEqual(out._proc, wrk)
        self.assertFalse(out._service_properties._is_hash_used)
        self.assertEqual(out._service_properties._id_hash, '')

    def test_to_kubernetes_raises(self):
        ''' to_kubernetes - should raise NotImplementedError
        '''
        out = bpmn_util.BPMNComponent({'@id':'Task_One'}, self._process, bpmn_util.WorkflowProperties())
        with self.assertRaises(NotImplementedError):
            out.to_kubernetes(None,None,None)


if __name__ == '__main__':
    unittest.main()
 
