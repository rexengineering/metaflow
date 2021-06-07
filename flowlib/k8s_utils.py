'''
Removes significant copy-pasta by defining simple utilities to
create a k8s Service, ServiceAccount, and Deployment.
'''
from base64 import b64encode
from typing import Mapping

from .config import (
    ETCD_CA_CERT,
    ETCD_CERT_CERT,
    ETCD_CERT_KEY,
    KAFKA_HOST,
    KAFKA_API_KEY,
    KAFKA_API_SECRET,
    KAFKA_SASL_MECHANISM,
    KAFKA_SECURITY_PROTOCOL,
    ETCD_HOSTS,
    REXFLOW_ROOT_PREFIX,
    FLOWD_HOST,
    FLOWD_PORT,
)

ETCD_ENV_MAP = {
    'REXFLOW_ETCD_CA_CERT': ETCD_CA_CERT,
    'REXFLOW_ETCD_CERT_CERT': ETCD_CERT_CERT,
    'REXFLOW_ETCD_CERT_KEY': ETCD_CERT_KEY,
}


def to_base64(file_loc):
    '''Accepts a file path, reads it, and encodes it into base64.
    Should only be called on small files.
    '''
    with open(file_loc, 'r') as f:
        return b64encode(f.read().encode())


def create_deployment(
    namespace, dns_safe_name, container, container_port, env, etcd_access=False,
    kafka_access=False, use_service_account=True, replicas=1, priority_class=None,
    health_props=None
):
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
                    'containers': [
                        {
                            'image': container,
                            'imagePullPolicy': 'Always',
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
    if priority_class is not None:
        deployment['spec']['template']['spec']['priorityClassName'] = priority_class
    env = env.copy()

    if etcd_access:
        env.append({
            "name": "ETCD_HOSTS",
            "value": ETCD_HOSTS,
        })
        env.append({
            "name": "REXFLOW_ROOT_PREFIX",
            "value": REXFLOW_ROOT_PREFIX,
        })
        env.extend([
            {
                "name": env_name,
                "value": ETCD_ENV_MAP[env_name],
            }
            for env_name in ETCD_ENV_MAP.keys()
            if ETCD_ENV_MAP[env_name] is not None
        ])
    if kafka_access:
        env_data = [
            ('REXFLOW_KAFKA_HOST', KAFKA_HOST),
            ('REXFLOW_KAFKA_API_KEY', KAFKA_API_KEY),
            ('REXFLOW_KAFKA_API_SECRET', KAFKA_API_SECRET),
            ('REXFLOW_KAFKA_SASL_MECHANISM', KAFKA_SASL_MECHANISM),
            ('REXFLOW_KAFKA_SECURITY_PROTOCOL', KAFKA_SECURITY_PROTOCOL),
        ]
        for env_var, value in env_data:
            if value is None:
                continue
            env.append({"name": env_var, "value": value})
    env.extend([{
        "name": "REXFLOW_FLOWD_HOST",
        "value": FLOWD_HOST,
    }, {
        "name": "REXFLOW_FLOWD_PORT",
        "value": FLOWD_PORT,
    }])

    spec = deployment['spec']['template']['spec']
    spec['containers'][0]['env'] = env
    if use_service_account:
        spec['serviceAccountName'] = dns_safe_name

    if health_props is not None:
        spec['containers'][0]['livenessProbe'] = {
            'httpGet': {
                'path': health_props.path,
                'port': container_port,
            },
            'initialDelaySeconds': health_props.initial_delay,
            'periodSeconds': health_props.period,
            'timeoutSeconds': health_props.timeout,
            'failureThreshold': health_props.failure_threshold,
        }
        spec['containers'][0]['readinessProbe'] = {
            'httpGet': {
                'path': health_props.path,
                'port': container_port,
            },
            'periodSeconds': health_props.period,
            'timeoutSeconds': health_props.timeout,
            'failureThreshold': health_props.failure_threshold,
        }
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


def create_service(namespace, dns_safe_name, port, target_port=None):
    if target_port is None:
        target_port = port
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
                    'port': port,
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


def get_rexflow_component_annotations(bpmn_component):
    return {
        "rexflow.rexhomes.com/bpmn-component-id": bpmn_component.id,
        "rexflow.rexhomes.com/bpmn-component-name": bpmn_component.name,
        "rexflow.rexhomes.com/wf-id": bpmn_component.workflow_properties.id,
    }
