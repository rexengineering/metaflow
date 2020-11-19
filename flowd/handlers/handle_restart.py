from collections import OrderedDict as odict
import logging
import uuid

import xmltodict
import json

from flowlib import bpmn, workflow
from flowlib.etcd_utils import get_etcd


def handler(request):
    '''
    Arguments:
        request: gRPC RestartRequest request object.
    Returns:
        A Python dictionary that can be serialized to a JSON object.
    '''
    logger = logging.getLogger()
    result = dict()
    instance_id = request.wf_instance_id
    instance_prefix = f'/rexflow/instances/{instance_id}'

    print("about to restart instance", instance_id, flush=True)
    etcd = get_etcd()

    # First check to see that the thing is in the `ERROR` state.
    state = etcd.get(f'{instance_prefix}/state')[0]
    print(state, flush=True)
    assert state == b'ERROR', "Can only retry instances in ERROR state"

    # NOTE: As of now, there's not a really good way to go from WF Instance id
    # to WF Id. However, Jon's code requires that we construct a Workflow object
    # before creating a WorkflowInstance object, which thus requires we get
    # the WF Id. As such, the following is a hack.
    # Recall that we've stored the headers already:
    headers = json.loads(etcd.get(f'{instance_prefix}/headers')[0].decode())
    wf_id = headers['X-Rexflow-Wf-Id']  # note this will change.
    # also note: we retrieve the headers twice. We won't need to 

    print("wf_id is: ", wf_id, flush=True)

    # now we can get the Workflow Object
    wf_obj = workflow.Workflow.from_id(wf_id)
    wf_instance_obj = workflow.WorkflowInstance(wf_obj, id=request.wf_instance_id)

    return wf_instance_obj.retry()
