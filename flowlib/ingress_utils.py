import logging
import re
from subprocess import run

from flowlib.constants import (
    HOST_SUFFIX,
    flow_result,
    get_ingress_object_name,
    get_ingress_labels,
    WorkflowKeys,
)
from flowlib.etcd_utils import get_etcd, get_keys_from_prefix
from flowlib.config import INGRESS_TEMPLATE
from flowlib.start_event import BPMNStartEvent


def get_current_occupant(hostname: str) -> str:
    '''Returns the id of the Workflow occupying `hostname` if one exists; else returns None
    '''
    etcd = get_etcd()
    all_wf_ids_with_host = set(
        key.split('/')[3]
        for key in get_keys_from_prefix(WorkflowKeys.ROOT)
        if len(key.split('/')) == 5 and key.split('/')[4] == HOST_SUFFIX.lstrip('/')
    )
    logging.info(f"All wf_ids: {all_wf_ids_with_host}")

    for wf_id in all_wf_ids_with_host:
        wf_host = etcd.get(WorkflowKeys.host_key(wf_id))[0].decode()
        if wf_host == hostname:
            return wf_id

    return None


def get_k8s_ingress_specs(wf_obj, hostname, args):
    template = INGRESS_TEMPLATE
    start_event = wf_obj.process.start_event  # type: BPMNStartEvent
    service_host = start_event.envoy_host
    port = start_event.service_properties.port
    assert "cicd.rexhomes.com/deployed-by: rexflow" in INGRESS_TEMPLATE, \
        "Deployer of REXFlow provided an invalid Ingress Template."

    label_dict = get_ingress_labels(wf_obj)
    if '<<wf_id_label>>' not in template:
        raise RuntimeError(
            "Invalid config: deployer of rexflow did not supply <<wf_id_label>> template var."
        )
    template = template.replace("<<wf_id_label>>", f"{label_dict['key']}: {label_dict['value']}")

    name = get_ingress_object_name(hostname)
    template = template.replace('<<name>>', name)
    template = template.replace('<<hostname>>', hostname)
    template = template.replace('<<service_host>>', service_host)
    template = template.replace('<<service_port>>', str(port))

    for arg_string in args:
        placeholder = f'<<{arg_string[arg_string.find("=")]}>>'
        value = arg_string[arg_string.find("=") + 1:]
        if placeholder not in template:
            raise RuntimeError(
                f"Provided option {placeholder} not found in Ingress Template."
            )
        template = template.replace(placeholder, value)

    print(template, flush=True)
    return template


def _cleanup_previous_ingress(wf_obj):
    '''Removes the k8s objects for ingress. wf_obj is provided
    only to determine the label selector for the necessary Ingress objects.

    NOTE: This does NOT update the host field of the deployment in Etcd.
    '''
    logging.info(f"Removing cleaning up ingress resources for {wf_obj.id}.")

    # We rely upon the label we inserted in get_k8_ingress_specs. But we still
    # need to know which _type_ of object to remove, so we get that through
    # a regex.
    kind_set = set(re.findall(r"^kind: .+$", INGRESS_TEMPLATE, flags=re.MULTILINE))
    k8s_resource_types = [line[len('kind: '):] for line in kind_set]
    label_dict = get_ingress_labels(wf_obj)
    label = f"{label_dict['key']}={label_dict['value']}"
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
                f"Failed to cleanup ingress on {wf_obj.id}: {kubectl_output.stderr}"
            )
        output += f"{resource_type}: {kubectl_output.stdout}\n"
    return output


def _apply_ingress(hostname: str, wf_obj, args):
    logging.info(f"Applying ingress {hostname} for {wf_obj.id}.")
    specs = get_k8s_ingress_specs(wf_obj, hostname, args)
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
            f"Failed to setup ingress on {wf_obj.id}: {kubectl_output.stderr}"
        )


def delete_ingress(workflow):
    etcd = get_etcd()
    if not etcd.delete(workflow.keys.host):
        msg = f"couldn't remove the host key on wf {workflow.id}"
        logging.error(msg)
        return flow_result(-1, msg)
    kubectl_output = _cleanup_previous_ingress(workflow)
    return flow_result(0, f"Cleaned up ingress for wf {workflow.id}: {kubectl_output}")


def switch_ingress(hostname, to_wf, from_wf, args):
    try:
        etcd = get_etcd()
        _cleanup_previous_ingress(to_wf)
        _cleanup_previous_ingress(from_wf)
        etcd.delete(from_wf.keys.host)
        _apply_ingress(hostname, to_wf, args)
        etcd.put(to_wf.keys.host, hostname)

        return flow_result(
            0,
            f"Successfully migrated ingress {hostname} from {from_wf.id} to {to_wf.id}."
        )
    except Exception as exn:
        msg = f"Failed to migrate ingress {hostname} from {from_wf.id} to {to_wf.id}."
        logging.exception(msg, exc_info=exn)
        return flow_result(-1, f"{msg}: {exn}")


def set_ingress(hostname: str, wf_obj, args):
    try:
        etcd = get_etcd()
        # TODO: put some sort of check here.
        _cleanup_previous_ingress(wf_obj)
        if not etcd.put(wf_obj.keys.host, hostname):
            return flow_result(-1, f"Failed to set ingress on {wf_obj.id}")

        _apply_ingress(hostname, wf_obj, args)

        return flow_result(
            0,
            f"Successfully pointed ingress {hostname} to {wf_obj.id}."
        )
    except Exception as exn:
        msg = f"Failed to assign ingress {hostname} to {wf_obj.id}."
        logging.exception(msg, exc_info=exn)
        return flow_result(-1, f"{msg}: {exn}")

