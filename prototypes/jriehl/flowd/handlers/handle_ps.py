import logging

from flowlib import flow_pb2
from flowlib import etcd_utils


class PSHandlers:
    def __init__(self):
        self.etcd = etcd_utils.get_etcd(is_not_none=True)

    def handle_single_deployment(self, deployment_id):
        return etcd_utils.get_dict_from_prefix(
            f'/rexflow/workflows/{deployment_id}',
            keys={'state'},
            value_transformer=lambda bstr: bstr.decode('utf-8')
        )

    def handle_some_deployments(self, ids):
        result = dict()
        for deployment_id in ids:
            result[deployment_id] = self.handle_single_deployment(deployment_id)
        return result

    def handle_all_deployments(self):
        all_ids = set(
            key.split('/')[3]
            for key in etcd_utils.get_keys_from_prefix('/rexflow/workflows/')
        )
        return self.handle_some_deployments(all_ids)

    def handle_single_instance(self, instance_id):
        return etcd_utils.get_dict_from_prefix(
            f'/rexflow/instances/{instance_id}',
            value_transformer=lambda bstr: bstr.decode('utf-8')
        )

    def handle_some_instances(self, ids):
        result = dict()
        for instance_id in ids:
            result[instance_id] = self.handle_single_instance(instance_id)
        return result

    def handle_all_instances(self):
        all_ids = set(
            key.split('/')[3]
            for key in etcd_utils.get_keys_from_prefix('/rexflow/instances/')
        )
        return self.handle_some_instances(all_ids)


def handler(request):
    result = None
    handlers = PSHandlers()
    request_kind = request.kind
    if request_kind == flow_pb2.RequestKind.DEPLOYMENT:
        if request.ids:
            result = handlers.handle_some_deployments(request.ids)
        else:
            result = handlers.handle_all_deployments()
    elif request_kind == flow_pb2.RequestKind.INSTANCE:
        if request.ids:
            result = handlers.handle_some_instances(request.ids)
        else:
            result = handlers.handle_all_instances()
    else:
        raise ValueError(f'Unknown PS request kind ({request_kind})!')
    return result
