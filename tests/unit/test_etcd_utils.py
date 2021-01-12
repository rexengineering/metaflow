import unittest
from unittest.mock import Mock, patch, MagicMock

import etcd3  # import before our subject module

from flowlib import etcd_utils
import copy
import xmltodict

from collections import OrderedDict
from flowlib import catch_event

class TestEtcdUtils(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print('\n TestEtcdUtils\n==============================')

    def test_init_etcd_raises(self):
        '''Call init_etcd where no client is returned. Raises AssertionError'''
        mockClient = Mock()
        mockClient.get = Mock(side_effect=AssertionError)
        etcd3.client = Mock(return_value=mockClient)
        etcd_utils._etcd = None

        with self.assertRaises(AssertionError):
            etcd_utils.init_etcd()

        assert mockClient.get.called

    def test_init_etcd(self):
        '''Call init_etcd where client is returned.'''
        mockClient = Mock()
        mockClient.get = Mock(return_value=Mock())
        etcd3.client = Mock(return_value=mockClient)
        etcd_utils._etcd = None
        etcd_utils.init_etcd()

        assert mockClient.get.called

    def test_get_etcd_exists(self):
        '''Call get_etcd to return existing etcd3 instance'''
        test_value = 'foobar'
        etcd_utils._etcd = Mock(return_value=test_value)
        res = etcd_utils.init_etcd()
        self.assertEqual(res(), test_value)

    def test_init_no_args_raises(self):
        '''Call init_etcd with arguments and _etcd not None. Raises ValueError'''
        etcd_utils._etcd = Mock()
        etcd_utils.init_etcd()
        with self.assertRaises(ValueError):
            etcd_utils.init_etcd([1,2,3])
 
    def test_get_etcd_is_not_none_raises(self):
        '''Call get_etcd with _etcd None and is_not_none True. Raises AssertionError'''
        etcd_utils._etcd = None
        with self.assertRaises(AssertionError):
            etcd_utils.get_etcd(is_not_none=True)

    def test_get_etcd_is_not_none_false(self):
        '''Call get_etcd with etcd None and is_not_none False.'''
        mockClient = Mock()
        mockClient.get = Mock(return_value=Mock())
        etcd3.client = Mock(return_value=mockClient)
        etcd_utils._etcd = None
        etcd_utils.get_etcd(is_not_none=False)
        assert mockClient.get.called

    def test_get_etcd(self):
        '''Call get_etcd to return existing etcd3 instance'''
        test_value = 'foobar'
        etcd_utils._etcd = Mock(return_value=test_value)
        res = etcd_utils.get_etcd(is_not_none=False)
        self.assertEqual(res(), test_value)

class TestTransitionState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print('\n TestTransitionState\n==============================')

        cls.mockClient = Mock()
        cls.mockClient.get = Mock(return_value=['this'])
        mockLock = Mock()
        mockLock.__enter__ = Mock(return_value='hello')
        mockLock.__exit__ = Mock()
        cls.mockClient.lock = Mock(return_value=mockLock)
        cls.mockClient.replace = Mock(return_value=True)
        # etcd3.client = Mock(return_value=cls.mockClient)

    def test_bad_cur_state(self):
        self.mockClient.get = Mock(return_value=['those'])
        self.mockClient.replace = Mock(return_value=True)
        res = etcd_utils.transition_state(self.mockClient, 'statekey', ['this','that'], 'them')
        self.assertFalse(res)

    def test_happy_path(self):
        self.mockClient.get = Mock(return_value=['this'])
        self.mockClient.replace = Mock(return_value=True)
        res = etcd_utils.transition_state(self.mockClient, 'statekey', ['this','that'], 'them')
        self.assertTrue(res)
    
    def test_fail_replace(self):
        self.mockClient.get = Mock(return_value=['this'])
        self.mockClient.replace = Mock(return_value=False)
        res = etcd_utils.transition_state(self.mockClient, 'statekey', ['this','that'], 'them')
        self.assertFalse(res)


class TestEtcdDict(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print('\n TestEtcdDict\n==============================')

    def test_from_dict_simple(self):
        '''EtcdDict with simple dict just returns that dict'''
        simple = {'/a/b/c/d':'hello', '/a/b/c/e':'world'}
        res = etcd_utils.EtcdDict.from_dict(simple)
        self.assertEqual(simple, res)

    def test_from_dict_complex(self):
        '''EtcdDict with complex dict returns something weird'''
        inDict = {'/a/b/c/d': {'e': {'a':'hello', 'b':'world'}}}
        otDict = {}
        res = etcd_utils.EtcdDict.from_dict(inDict)
        print(res)
        self.assertEqual(res,otDict)


if __name__ == '__main__':
    unittest.main()
