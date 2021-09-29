import functools
import os
import unittest

from flowd.handlers import handle_run, handle_apply, handle_ps
from flowlib import flow_pb2, workflow
from flowlib import etcd_utils
from flowlib.constants import WorkflowInstanceKeys
from tests import test_metadata


TESTS_PATH = os.path.split(__file__)[0]
SKIP_MESSAGE = 'either configured to point at a non-local etcd, or no local etcd is available'


class DummyInstance:
    counter: int = 0

    def __init__(self, parent, id = None, *args, **kws):
        self.args = args
        self.kws = kws
        self.parent = parent
        if id is None:
            DummyInstance.counter += 1
            self.iid = f'{parent.id}-{DummyInstance.counter}'
        else:
            self.iid = id
        self.keys = WorkflowInstanceKeys(self.iid)
        self.start_result = {"message": "", "status": 0, "id": self.iid}

    def start(self, *args, **kws):
        return self.start_result


@functools.cache
def has_local_etcd():
    endpoints = etcd_utils._get_etcd_endpoints()
    if len(endpoints) == 1 and endpoints[0]['host'] == 'localhost':
        try:
            etcd = etcd_utils.get_etcd()
            return bool(etcd)
        except:
            return False
    return False


class TestHandleRun(unittest.TestCase):
    def _do_test(self, actual_test):
        # Monkey-patch the workflow instance class...
        self.WorkflowInstance = workflow.WorkflowInstance
        workflow.WorkflowInstance = DummyInstance
        try:
            # !!!DANGER!!! This test assumes you are testing on a local etcd and
            # don't mind if we nuke all the instance metadata.
            etcd = etcd_utils.get_etcd()
            etcd.delete_prefix('/rexflow')
            with open(os.path.join(TESTS_PATH, 'super_happy.bpmn')) as fileobj:
                spec = fileobj.read()
            request = flow_pb2.ApplyRequest(bpmn_xml=spec, stopped=False)
            result = handle_apply.handler(request)
            did = result['wf_id']
            wf_deployment = workflow.Workflow.from_id(did)
            etcd.put(wf_deployment.keys.state, b'RUNNING')
            actual_test(wf_deployment)
        finally:
            # Un-monkey that patch so other tests have a known good starting point!
            workflow.WorkflowInstance = self.WorkflowInstance

    @unittest.skipUnless(has_local_etcd(), SKIP_MESSAGE)
    def test_run_with_metadata(self):
        def _actual_test(wf_deployment: workflow.Workflow):
            did = wf_deployment.id
            user_data = {'user': 'test@rexhomes.com'}
            request = flow_pb2.RunRequest(
                workflow_id=did,
                metadata=test_metadata.dict_to_metadata(user_data)
            )
            result = handle_run.handler(request)
            self.assertIn('id', result)
            iid = result['id']
            instance = self.WorkflowInstance(wf_deployment, iid)
            self.assertTrue(bool(instance.keys.metadata))
            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
                ids=[iid],
                include_kubernetes=False
            )
            result = handle_ps.handler(request)
            print(result)
            self.assertEqual(result[iid]['metadata'], user_data)
        self._do_test(_actual_test)

    @unittest.skipUnless(has_local_etcd(), SKIP_MESSAGE)
    def test_run_without_metadata(self):
        def _actual_test(wf_deployment: workflow.Workflow):
            did = wf_deployment.id
            request = flow_pb2.RunRequest(workflow_id=did)
            result = handle_run.handler(request)
            self.assertIn('id', result)
            iid = result['id']
            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
                ids=[iid],
                include_kubernetes=False
            )
            result = handle_ps.handler(request)
            self.assertEqual(result[iid]['metadata'], {})
        self._do_test(_actual_test)


    @unittest.skipUnless(has_local_etcd(), SKIP_MESSAGE)
    def test_run_with_multiple_metadata(self):
        def _actual_test(wf_deployment: workflow.Workflow):
            did = wf_deployment.id
            user_data_0 = {'user': 'test-0@rexhomes.com'}
            request = flow_pb2.RunRequest(
                workflow_id=did,
                metadata=test_metadata.dict_to_metadata(user_data_0)
            )
            result = handle_run.handler(request)
            self.assertIn('id', result)
            iid_0 = result['id']

            user_data_1 = {'user': 'test-1@rexhomes.com'}
            request = flow_pb2.RunRequest(
                workflow_id=did,
                metadata=test_metadata.dict_to_metadata(user_data_1)
            )
            result = handle_run.handler(request)
            self.assertIn('id', result)
            iid_1 = result['id']

            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
            )
            result = handle_ps.handler(request)
            self.assertEqual(len(result), 2)
            self.assertIn(iid_0, result)
            self.assertIn(iid_1, result)
            self.assertEqual(result[iid_0]['metadata'], user_data_0)
            self.assertEqual(result[iid_1]['metadata'], user_data_1)

            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
                metadata=test_metadata.dict_to_metadata(user_data_0)
            )
            result = handle_ps.handler(request)
            self.assertEqual(len(result), 1)
            self.assertIn(iid_0, result)
            self.assertEqual(result[iid_0]['metadata'], user_data_0)

            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
                metadata=test_metadata.dict_to_metadata(user_data_1)
            )
            result = handle_ps.handler(request)
            self.assertEqual(len(result), 1)
            self.assertIn(iid_1, result)
            self.assertEqual(result[iid_1]['metadata'], user_data_1)

            request = flow_pb2.PSRequest(
                kind=flow_pb2.RequestKind.INSTANCE,
                metadata=test_metadata.dict_to_metadata({'orthogonal': 'true'})
            )
            result = handle_ps.handler(request)
            self.assertEqual(len(result), 0)
        self._do_test(_actual_test)


if __name__ == '__main__':
    unittest.main()
