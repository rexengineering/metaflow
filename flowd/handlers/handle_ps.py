from io import StringIO
import json
import logging

from flowlib import flow_pb2
from flowlib import etcd_utils
from flowlib.constants import WorkflowKeys, WorkflowInstanceKeys, States
from flowlib.workflow import Workflow
from flowlib.ingress_utils import get_host_dict


class PSHandlers:
    def __init__(self):
        self.etcd = etcd_utils.get_etcd(is_not_none=True)

    def handle_single_deployment(self, deployment_id, include_kubernetes):
        keys = {'state'}
        response = etcd_utils.get_dict_from_prefix(
            WorkflowKeys.key_of(deployment_id),
            keys=keys,
            value_transformer=lambda bstr: bstr.decode('utf-8')
        )
        if include_kubernetes:
            # get the kubernetes spec. Can't directly query S3 because not all
            # flowd deployments will have access to s3. Therefore, we get the
            # cached value if cached, else recompute from scratch.
            wf = Workflow.from_id(deployment_id)
            k8s_specs_stream = StringIO()
            wf.process.to_istio(stream=k8s_specs_stream)
            response['k8s_specs'] = k8s_specs_stream.getvalue()

        # Now must see if there's a host involved.
        host_dict = get_host_dict(deployment_id)
        if bool(host_dict):
            response['ingress'] = host_dict
        return response

    def handle_some_deployments(self, ids, include_kubernetes):
        result = dict()
        for deployment_id in ids:
            result[deployment_id] = self.handle_single_deployment(
                deployment_id, include_kubernetes
            )
        return result

    def handle_all_deployments(self, include_kubernetes):
        all_ids = set(
            key.split('/')[3]
            for key in etcd_utils.get_keys_from_prefix(WorkflowKeys.ROOT)
        )
        return self.handle_some_deployments(all_ids, include_kubernetes)

    def handle_single_instance(self, instance_id):
        result = etcd_utils.get_dict_from_prefix(
            WorkflowInstanceKeys.key_of(instance_id),
            value_transformer=lambda bstr: bstr.decode('utf-8')
        )
        if result['state'] in [States.ERROR, States.STOPPED] and  'content_type' in result \
                and result['content_type'] == 'application/json':
            # Then the result *should* be a JSON-loadable item. If so,
            # we load it and splat it.
            try:
                splat_result = json.loads(result['result'])
                del result['result']
                splat_result.update(result)
                result = splat_result
            except Exception as exn:
                logging.exception('unexpected error loading json of error instance:', exc_info=exn)

        return result

    def handle_some_instances(self, ids):
        result = dict()
        for instance_id in ids:
            result[instance_id] = self.handle_single_instance(instance_id)
        return result

    def handle_all_instances(self):
        all_ids = set(
            key.split('/')[3]
            for key in etcd_utils.get_keys_from_prefix(WorkflowInstanceKeys.ROOT)
        )
        return self.handle_some_instances(all_ids)


def handler(request):
    result = None
    handlers = PSHandlers()
    request_kind = request.kind
    if request_kind == flow_pb2.RequestKind.DEPLOYMENT:
        include_kubernetes = request.include_kubernetes
        if request.ids:
            result = handlers.handle_some_deployments(request.ids, include_kubernetes)
        else:
            result = handlers.handle_all_deployments(include_kubernetes)
    elif request_kind == flow_pb2.RequestKind.INSTANCE:
        if request.ids:
            result = handlers.handle_some_instances(request.ids)
        else:
            result = handlers.handle_all_instances()
    else:
        raise ValueError(f'Unknown PS request kind ({request_kind})!')
    return result
