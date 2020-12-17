import unittest
from unittest.mock import Mock, patch, MagicMock

from flowlib import etcd_utils
import copy
import xmltodict

from collections import OrderedDict
from flowlib import catch_event

class TestEtcdUtils(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print('\n TestEtcdUtils\n==============================')

    @patch('flowlib.etcd_utils.etcd3')
    @patch('flowlib.etcd_utils.etcd3.client')
    def test_init_etcd_raises(self, mockClient, mockEtcd3):
        '''Call init_etcd where no client is returned. Raises AssertionError'''
        with self.assertRaises(AssertionError):
            mockClient.get = Mock(side_effect=AssertionError)
            mockEtcd3.client = Mock(return_value=mockClient)
            etcd_utils.init_etcd()

@patch('flowlib.etcd_utils.etcd3')
@patch('flowlib.etcd_utils.etcd3.client')
class TestEtcdUtils0(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print('\n TestEtcdUtils0\n==============================')

    def test_init_etcd(self, mockClient, mockEtcd3):
        '''Call init_etcd where no client is returned.'''
        mockClient.get = Mock(return_value='hello')
        mockEtcd3.client = Mock(return_value=mockClient)
        ret = etcd_utils.init_etcd()

    def test_init_no_args_raises(self, mockClient, mockEtcd3):
        '''Call init_etcd with arguments and _etcd not None. Raises ValueError'''
        etcd_utils.init_etcd()
        with self.assertRaises(ValueError):
            etcd_utils.init_etcd([1,2,3])

class TestEtcdGetEtcd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print('\n TestEtcdGetEtcd\n==============================')
   
    def test_is_not_none_raises(self):
        with self.assertRaises(AssertionError):
            etcd_utils.get_etcd(is_not_none=True)


if __name__ == '__main__':
    unittest.main()
