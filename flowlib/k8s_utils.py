'''
Removes significant copy-pasta by defining simple utilities to
create a k8s Service, ServiceAccount, and Deployment.
'''
from typing import Mapping

from .bpmn_util import BPMNComponent


def create_deployment(namespace, dns_safe_name, container, container_port, env, replicas=1):
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': dns_safe_name,
            'namespace': namespace,
        },
        'spec': {
            'replicas': replicas,
            'selector': {
                'matchLabels': {
                    'app': dns_safe_name,
                },
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': dns_safe_name,
                    },
                },
                'spec': {
                    'serviceAccountName': dns_safe_name,
                    'containers': [
                        {
                            'image': container,
                            'imagePullPolicy': 'IfNotPresent',
                            'name': dns_safe_name,
                            'ports': [
                                {
                                    'containerPort': container_port,
                                },
                            ],
                        },
                    ],
                },
            },
        },
    }
    if env is not None:
        deployment['spec']['template']['spec']['containers'][0]['env'] = env
    return deployment


def create_serviceaccount(namespace, dns_safe_name):
    service_account = {
        'apiVersion': 'v1',
        'kind': 'ServiceAccount',
        'metadata': {
            'name': dns_safe_name,
            'namespace': namespace,
        },
    }
    return service_account


def create_rexflow_ingress_vs(namespace, dns_safe_name, uri_prefix, dest_port, dest_host):
    # TODO: We need to put this behind a "Development" feature flag.
    # It's very useful for debugging purposes on docker-desktop to have a virtualservice
    # so that we can do `curl localhost/my-service`, but this will break our helm charts
    # if we put it in prod (that's not to mention we don't want everything automatically
    # visible to the outside world)

    virtual_service = {
        'apiVersion': 'networking.istio.io/v1alpha3',
        'kind': 'VirtualService',
        'metadata': {
            'name': dns_safe_name,

            # hardcode it as "default" because otherwise it doesn't work.
            'namespace': "default",
        },
        'spec': {
            'hosts': ['*'],
            'gateways': ['rexflow-gateway'],
            'http': [
                {
                    'match': [{'uri': {'prefix': uri_prefix}}],
                    'rewrite': {'uri': '/'},
                    'route': [
                        {
                            'destination': {
                                'port': {'number': dest_port},
                                'host': dest_host
                            }
                        }
                    ]
                }
            ]
        }
    }
    return virtual_service


def create_service(namespace, dns_safe_name, target_port):
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': dns_safe_name,
            'labels': {
                'app': dns_safe_name,
            },
            'namespace': namespace,
        },
        'spec': {
            'ports': [
                {
                    'name': 'http',
                    'port': target_port,
                    'targetPort': target_port,
                }
            ],
            'selector': {
                'app': dns_safe_name,
            },
        },
    }
    return service


def create_deployment_affinity(service_name, anti_service_name):
    '''Creates k8s Affinity specification. `service_name` specifies a service next to which we
    wish to deploy something, and `anti_service_name` specifies the service next to which we
    do not wish to deploy. A typical use case is:

    `service_name` == the application for a Microservice Task in a Reliable WF
    `anti_service_name` == the application name for a python kafka helper service.
       ---> we want one of the kafka helper pods on the same node as the service, and
            we don't need more than one helper pod on one node (since that's dumb).
    '''
    affinity = {
        'podAffinity': {
            "requiredDuringSchedulingIgnoredDuringExecution": [{
                "labelSelector": {
                    "matchExpressions": [{
                        "key": "app",
                        "operator": "In",
                        "values": [service_name],
                    }],
                },
                "topologyKey": "kubernetes.io/hostname",
            }]
        },
        'podAntiAffinity': {
            'preferredDuringSchedulingIgnoredDuringExecution': [{
                "weight": 100,
                "podAffinityTerm": {
                    "labelSelector": {
                        "matchExpressions": [{
                            "key": "app",
                            "operator": "In",
                            "values": [anti_service_name],
                        }],
                    },
                    "topologyKey": "kubernetes.io/hostname",
                }
            }]
        }
    }
    return affinity


def add_labels(k8s_spec, labels: Mapping[str, str]):
    assert 'metadata' in k8s_spec, f"Bad k8s spec: should have metadata field\n{k8s_spec}"
    if 'labels' not in k8s_spec['metadata']:
        k8s_spec['metadata']['labels'] = {}

    if k8s_spec.get('kind', None) == 'Deployment':
        # must label the pod spec as well
        if 'metadata' not in k8s_spec['spec']['template']:
            k8s_spec['spec']['template']['metadata'] = {}
        add_labels(k8s_spec['spec']['template'], labels)

    for label_key in labels.keys():
        k8s_spec['metadata']['labels'][label_key] = labels[label_key]


def add_annotations(k8s_spec, annotations: Mapping[str, str]):
    assert 'metadata' in k8s_spec, f"Bad k8s spec: should have metadata field\n{k8s_spec}"
    if 'annotations' not in k8s_spec['metadata']:
        k8s_spec['metadata']['annotations'] = {}

    if k8s_spec.get('kind', None) == 'Deployment':
        # must annotate the pod spec as well
        if 'metadata' not in k8s_spec['spec']['template']:
            k8s_spec['spec']['template']['metadata'] = {}
        add_annotations(k8s_spec['spec']['template'], annotations)

    for annot_key in annotations.keys():
        k8s_spec['metadata']['annotations'][annot_key] = annotations[annot_key]


def get_rexflow_labels(wf_id):
    return {
        "cicd.rexhomes.com/deployed-by": "rexflow",
        "rexflow.rexhomes.com/wf-id": wf_id,
    }


def get_rexflow_component_annotations(bpmn_component: BPMNComponent):
    return {
        "rexflow.rexhomes.com/bpmn-component-id": bpmn_component.id,
        "rexflow.rexhomes.com/bpmn-component-name": bpmn_component.name,
        "rexflow.rexhomes.com/wf-id": bpmn_component.workflow_properties.id,
    }
