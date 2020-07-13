from collections import OrderedDict as odict
import logging
import uuid

import xmltodict

from ..probes import add_health_probe
from flowlib.etcd_utils import get_etcd


def handler(request):
    '''
    Arguments:
        request: gRPC apply request object.
    Returns:
        A Python dictionary that can be serialized to a JSON object.
    '''
    logger = logging.getLogger()
    result = dict()
    spec = xmltodict.parse(request.bpmn_xml, encoding='utf-8')
    if logger.level < logging.INFO:
        logging.debug(f'Received following BPMN specification:\n{spec}')
    proc = spec['bpmn:definitions']['bpmn:process']
    workflow_uuid = uuid.uuid1()
    proc_id = proc['@id']
    assert proc_id != 'flow', 'Your process name cannot be "flow", as it is a reserved prefix'
    workflow_id = f'{proc["@id"]}-{workflow_uuid.hex}'
    result[proc['@id']] = workflow_id
    etcd = get_etcd(is_not_none=True)
    workflow_prefix = f'/rexflow/workflows/{workflow_id}'
    etcd.put(
        workflow_prefix + '/proc',
        xmltodict.unparse(odict([('bpmn:process', proc)]))
    )
    etcd.put(workflow_prefix + '/state', 'STARTING')
    add_health_probe(workflow_id)
    return result
