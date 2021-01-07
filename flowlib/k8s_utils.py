'''
Removes significant copy-pasta by defining simple utilities to
create a k8s Service, ServiceAccount, and Deployment.
'''


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
