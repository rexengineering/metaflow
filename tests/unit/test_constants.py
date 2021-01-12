import unittest
from unittest.mock import Mock, patch, MagicMock

from flowlib import etcd_utils
import copy
import xmltodict

from collections import OrderedDict
from flowlib import constants

goodStates = ['COMPLETED', 'ERROR', 'RUNNING', 'START', 'STARTING', 'STOPPED', 'STOPPING', 'TRUE']

class TestConstants(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print('\n TestConstants\n==============================')

    def test_states(self):
        '''Assure that all expected states exist and no additional states have been added'''
        # this is the list of states that should be in constants.States
        # extract the states form the class
        sta = [
            stat
            for stat in vars(constants.States).keys()
            if stat[0:2] != '__'
        ]
        # check that each of the expected states exist
        for state in goodStates:
            self.assertIn(state, sta)
            sta.remove(state)
        # check that no "extra" states exist
        self.assertEqual(len(sta),0)

    def test_bstates(self):
        '''Verify that the bytearray conversion works for all states'''
        for state in goodStates:
            bstate = state.encode('utf-8')
            self.assertEqual(getattr(constants.BStates, state), bstate)

    def test_workflowkeys(self):
        '''verify that WorkflowKeys class produces expected values'''
        out = constants.WorkflowKeys('bogus')
        self.assertEqual(out.root,  '/rexflow/workflows/bogus')
        self.assertEqual(out.proc,  '/rexflow/workflows/bogus/proc')
        self.assertEqual(out.probe, '/rexflow/workflows/bogus/probes')
        self.assertEqual(out.state, '/rexflow/workflows/bogus/state')

    def test_workflowinstancekeys(self):
        '''verify that WorkflowInstanceKeys class produces expected values'''
        out = constants.WorkflowInstanceKeys('bogus')
        self.assertEqual(out.root,      '/rexflow/instances/bogus')
        self.assertEqual(out.proc,      '/rexflow/instances/bogus/proc')
        self.assertEqual(out.result,    '/rexflow/instances/bogus/result')
        self.assertEqual(out.state,     '/rexflow/instances/bogus/state')
        self.assertEqual(out.headers,   '/rexflow/instances/bogus/headers')
        self.assertEqual(out.payload,   '/rexflow/instances/bogus/payload')
        self.assertEqual(out.error_key, '/rexflow/instances/bogus/wasError')
        self.assertEqual(out.parent,    '/rexflow/instances/bogus/parent')
        self.assertEqual(out.end_event, '/rexflow/instances/bogus/end_event')
        self.assertEqual(out.traceid,   '/rexflow/instances/bogus/traceid')

    def test_split_key(self):
        '''verify that the split_key function works as expected'''
        with self.assertRaises(TypeError):
            constants.split_key()
        with self.assertRaises(AttributeError):
            constants.split_key(123)
        a,b = constants.split_key('a-b-c')
        self.assertEqual(a,'a-b')
        self.assertEqual(b,'c')

    def test_flow_result(self):
        '''verify that the flow_result function works as expected'''
        with self.assertRaises(TypeError):
            constants.flow_result()
        with self.assertRaises(TypeError):
            constants.flow_result(123)
        result = constants.flow_result(123,'abc')
        self.assertEqual(result,{'status':123, 'message':'abc'})
        result = constants.flow_result(123,'abc',w='x')
        self.assertEqual(result,{'status':123, 'message':'abc', 'w':'x'})

if __name__ == '__main__':
    unittest.main()
