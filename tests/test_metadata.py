'''Tests for metadata support.
'''
import json
import os.path
import time
from typing import List, Mapping, final
import unittest

from flowlib import flow_pb2
from flowlib.flowd_utils import get_flowd_connection
from tools import runwf


TESTS_PATH = os.path.split(__file__)[0]


def has_flowd():
    try:
        return runwf.flowd_ps_deployment()[0].startswith('Ok')
    except:
        return False


def flowd_apply(bpmn_spec: str):
    with get_flowd_connection(runwf.flowd_host, int(runwf.flowd_port)) as flowd:
        request = flow_pb2.ApplyRequest(bpmn_xml=bpmn_spec, stopped=False)
        response = flowd.ApplyWorkflow(request)
        return response


def flowd_wait(did: str, expected_state: str = 'RUNNING'):
    with get_flowd_connection(runwf.flowd_host, int(runwf.flowd_port)) as flowd:
        request = flow_pb2.ProbeRequest(ids=[did])
        response = flowd.ProbeWorkflow(request)
        assert response.status == 0
    while json.loads(runwf.flowd_ps_deployment([did])[1])[did]['state'] != expected_state:
        time.sleep(1)


def dict_to_metadata(mapping: Mapping[str, str]):
    return [
        flow_pb2.StringPair(key=the_key, value=the_value)
        for the_key, the_value in mapping.items()
    ]


def metadata_to_dict(pairs: List[flow_pb2.StringPair]):
    return {
        pair.key : pair.value
        for pair in pairs
    }


class TestFlowD(unittest.TestCase):
    @unittest.skipUnless(has_flowd(), 'Could not find or talk to the flow daemon.')
    def test_flowd_metadata(self):
        # Deploy a simple workflow...
        with open(os.path.join(TESTS_PATH, 'super_happy.bpmn')) as fileobj:
            spec = fileobj.read()
        result = flowd_apply(spec)
        self.assertEqual(result.status, 0, result.message)
        did = json.loads(result.data)['wf_id']
        flowd_wait(did)
        with get_flowd_connection(runwf.flowd_host, int(runwf.flowd_port)) as flowd:
            try:
                metadata_dict = {'user': 'test@rexhomes.com'}
                # Run the deployed workflow...
                request = flow_pb2.RunRequest(
                    workflow_id=did,
                    args=[],
                    stopped=False,
                    start_event_id='',
                    metadata=dict_to_metadata(metadata_dict)
                )
                response = flowd.RunWorkflow(request)
                self.assertEqual(response.status, 0)
                iid = json.loads(response.data)['id']
                try:
                    # Query the instances...
                    request = flow_pb2.PSRequest(kind=flow_pb2.RequestKind.INSTANCE, ids=[iid], include_kubernetes=False)
                    response = flowd.PSQuery(request)
                    self.assertEqual(response.status, 0)
                    data = json.loads(response.data)
                    self.assertIn('metadata', data[iid])
                    self.assertEqual(data[iid]['metadata'], metadata_dict)
                finally:
                    # Tear down the instance...
                    request = flow_pb2.DeleteRequest(kind=flow_pb2.RequestKind.INSTANCE, ids=[iid])
                    self.assertEqual(flowd.DeleteWorkflow(request).status, 0)
            finally:
                # Tear down the deployment...
                request = flow_pb2.StopRequest(kind=flow_pb2.RequestKind.DEPLOYMENT, ids=[did], force=True)
                self.assertEqual(flowd.StopWorkflow(request).status, 0)
                flowd_wait(did, 'STOPPED')
                request = flow_pb2.DeleteRequest(kind=flow_pb2.RequestKind.DEPLOYMENT, ids=[did])
                self.assertEqual(flowd.DeleteWorkflow(request).status, 0)


if __name__ == '__main__':
    unittest.main()
