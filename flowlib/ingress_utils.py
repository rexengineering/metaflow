import logging
import re
from subprocess import run

from flowlib.constants import (
    flow_result,
    get_ingress_object_name,
    WorkflowKeys,
    IngressHostKeys,
)
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix, get_dict_from_prefix
from flowlib.config import INGRESS_TEMPLATE
from flowlib.start_event import BPMNStartEvent
from flowlib.workflow import Workflow


def get_current_occupant(hostname: str) -> str:
    '''Returns the id of the Workflow occupying `hostname` if one exists; else returns None
    '''
    etcd = get_etcd()
    ingress_keys = IngressHostKeys(hostname)
    result = etcd.get(ingress_keys.workflow_id)[0]
    if result:
        return result.decode()
    else:
        return None


def get_host_dict(wf_id):
    response = {}
    # Now must see if there's a host involved.
    host_dict = get_dict_from_prefix(
        IngressHostKeys.ROOT,
        value_transformer=lambda bstr: bstr.decode('utf-8'),
    )
    for host in host_dict.keys():
        if host_dict[host]['workflow_id'] == wf_id:
            response[host_dict[host]['component_name']] = host

    return response


def get_k8s_ingress_specs(target_component, hostname, args=None):
    if args is None:
        args = {}
    template = INGRESS_TEMPLATE
    service_host = target_component.envoy_host
    port = target_component.service_properties.port

    assert "rexflow.rexhomes.com/wf-id: {" + "wf_id}" in INGRESS_TEMPLATE, \
        "rexflow deployment provided a bad Ingress Template: Missing wf_id label selector."
    assert "rexflow.rexhomes.com/component-id: {" + "component_id}" in INGRESS_TEMPLATE, \
        "rexflow deployment provided a bad Ingress Template: Missing component_id label selector."

    # expose a lot of info in case the user wants to slap a bunch
    # of lables on their k8s objects.
    update_args = {
        'wf_id': target_component.workflow_properties.id,
        'service_host': service_host,
        'service_port': port,
        'hostname': hostname,
        'component_id': target_component.id,
        'component_name': target_component.name,
        'name': get_ingress_object_name(hostname),
    }
    update_args.update(args)
    return template.format(**update_args)


def _cleanup_previous_ingress(target_component):
    '''Removes the k8s objects for ingress. target_component is provided
    only to determine the label selector for the necessary Ingress objects.

    NOTE: This does NOT update the host field of the deployment in Etcd.
    '''
    wf_id = target_component.workflow_properties.id
    logging.info(
        f"Cleaning up ingress resources for {target_component.name} in wf {wf_id}.")

    # We rely upon the label we inserted in get_k8_ingress_specs. But we still
    # need to know which _type_ of object to remove, so we get that through
    # a regex.
    kind_set = set(re.findall(r"^kind: .+$", INGRESS_TEMPLATE, flags=re.MULTILINE))
    k8s_resource_types = [line[len('kind: '):] for line in kind_set]
    label = f"rexflow.rexhomes.com/wf-id={wf_id}"
    label += f",rexflow.rexhomes.com/component-id={target_component.id}"
    output = ""
    for resource_type in k8s_resource_types:
        kubectl_output = run(
            ['kubectl', 'delete', resource_type, '-n', 'rexflow', '-l', label],
            capture_output=True,
            text=True,
        )
        if kubectl_output.returncode != 0:
            logging.error(f'Error from Kubernetes:\n{kubectl_output.stderr}')
            raise RuntimeError(
                f"Failed to cleanup ingress on {wf_id} {target_component.name}: "
                f"{kubectl_output.stderr}"
            )
        output += f"{resource_type}: {kubectl_output.stdout}\n"
    return output


def _apply_ingress(hostname: str, target_component, args):
    wf_id = target_component.workflow_properties.id
    logging.info(
        f"Applying ingress {hostname} for {target_component.name} {wf_id}.")
    specs = get_k8s_ingress_specs(target_component, hostname, args)
    kubectl_output = run(
        ['kubectl', 'apply', '-n', 'rexflow', '-f', '-'],
        input=specs,
        capture_output=True,
        text=True,
    )
    if kubectl_output.stdout:
        logging.info(f'Got following output from Kubernetes:\n{kubectl_output.stdout}')
    if kubectl_output.returncode != 0:
        logging.error(f'Error from Kubernetes:\n{kubectl_output.stderr}')
        raise RuntimeError(
            f"Failed to setup ingress on {target_component.name}: {kubectl_output.stderr}"
        )


def delete_ingress(host, wf_id, component_name=None, component_id=None):
    wf_obj = Workflow.from_id(wf_id)
    if component_id is not None:
        bpmn_component = wf_obj.process.component_map[component_id]
        component_name = bpmn_component.name
    else:
        assert component_name is not None, "Must specify component_id or component_name"
        bpmn_component = list(filter(
            lambda x: x.name == component_name,
            wf_obj.process.all_components
        ))[0]
        component_id = bpmn_component.id
    etcd = get_etcd()
    host_keys = IngressHostKeys(host)
    assert etcd.get(host_keys.workflow_id)[0].decode() == wf_id, \
        "Provided wf_id and host don't match."
    assert etcd.get(host_keys.component_name)[0].decode() == component_name, \
        "Provided component name and host don't match."

    etcd.delete(host_keys.workflow_id)
    etcd.delete(host_keys.component_name)
    kubectl_output = _cleanup_previous_ingress(bpmn_component)
    return flow_result(
        0,
        f"Cleaned up ingress for wf {wf_id}, {component_name}: {kubectl_output}"
    )


def set_ingress(hostname: str, wf_id, component_name=None, component_id=None, args=None):
    wf_obj = Workflow.from_id(wf_id)
    if component_id is not None:
        bpmn_component = wf_obj.process.component_map[component_id]
        component_name = bpmn_component.name
    else:
        assert component_name is not None, "Must specify component_id or component_name"
        bpmn_component = list(filter(
            lambda x: x.name == component_name,
            wf_obj.process.all_components
        ))[0]
    try:
        host_keys = IngressHostKeys(hostname)
        etcd = get_etcd()

        _cleanup_previous_ingress(bpmn_component)
        if not etcd.put(host_keys.workflow_id, wf_id):
            return flow_result(-1, f"Failed to set ingress on {wf_id}")

        if not etcd.put(host_keys.component_name, component_name):
            return flow_result(-1, f"Failed to set ingress on {component_name}")

        _apply_ingress(hostname, bpmn_component, args)

        return flow_result(
            0,
            f"Successfully pointed ingress {hostname} to {wf_id} {component_name}."
        )
    except Exception as exn:
        msg = f"Failed to assign ingress {hostname} to {wf_obj.id}."
        logging.exception(msg, exc_info=exn)
        return flow_result(-1, f"{msg}: {exn}")

