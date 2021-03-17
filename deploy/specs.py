from flowlib.config import (
    DEFAULT_XGW_IMAGE,
    DEFAULT_THROW_IMAGE,
    DEFAULT_CATCH_IMAGE,
    DEFAULT_REXFLOW_VERSION,
)

# Value for the kafka cluster of the dev deployment.
DEV_KAFKA_HOST = 'my-cluster-kafka-bootstrap.kafka:9092'

rexflow_namespace_spec = {
    'apiVersion': 'v1',
    'kind': 'Namespace',
    'metadata': {'name': 'rexflow'}
}

etcd_service_acct_spec = {
    'apiVersion': 'v1',
    'kind': 'ServiceAccount',
    'metadata': {'name': 'rexflow-etcd', 'namespace': 'rexflow'}
}

etcd_service_specs = {
    'apiVersion': 'v1',
    'kind': 'Service',
    'metadata': {
        'labels': {'app': 'rexflow-etcd'},
        'name': 'rexflow-etcd',
        'namespace': 'rexflow',
    },
    'spec': {
        'ports': [{'name': 'grpc', 'port': 2379, 'targetPort': 2379},
                  {'name': 'grpc2', 'port': 2380, 'targetPort': 2380}],
        'selector': {'app': 'rexflow-etcd'},
    },
}

etcd_deployment_spec = {
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': 'rexflow-etcd'},
    'spec': {
        'replicas': 1,
        'selector': {'matchLabels': {'app': 'rexflow-etcd'}},
        'template': {
            'metadata': {'labels': {'app': 'rexflow-etcd'}},
            'spec': {
                'containers': [
                    {
                        'image': 'quay.io/coreos/etcd',
                        'imagePullPolicy': 'IfNotPresent',
                        'name': 'rexflow-etcd',
                        'command': [
                            'etcd',
                            '--listen-client-urls=http://0.0.0.0:2379',
                            '--advertise-client-urls=http://0.0.0.0:2379',
                        ],
                        'ports': [{'containerPort': 2379}, {'containerPort': 2380}],
                    }
                ],
                'serviceAccountName': 'rexflow-etcd',
            }
        }
    }
}

flowd_service_acct_spec = {
    'apiVersion': 'v1',
    'kind': 'ServiceAccount',
    'metadata': {'name': 'flowd', 'namespace': 'rexflow'}
}

flowd_service_specs = {
    'rexflow': {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'labels': {'app': 'flowd'},
            'name': 'flowd',
            'namespace': 'rexflow',
        },
        'spec': {
            'ports': [{'name': 'grpc', 'port': 9001, 'targetPort': 9001},
                      {'name': 'http', 'port': 9002, 'targetPort': 9002}],
            'selector': {'app': 'flowd'},
        },
    },
    'default': {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': 'flowd',
            'namespace': 'default',
        },
        'spec': {
            'type': 'ExternalName',
            'externalName': 'flowd.rexflow.svc.cluster.local',
            'ports': [{'name': 'grpc', 'port': 9001},
                      {'name': 'http', 'port': 9002}],
            'selector': {'app': 'flowd'},
        },
    },
}

mk_flowd_deployment_spec = lambda etcd_host, kafka_enabled : {  # noqa
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': 'flowd'},
    'spec': {
        'replicas': 1,
        'selector': {'matchLabels': {'app': 'flowd'}},
        'template': {
            'metadata': {'labels': {'app': 'flowd'}},
            'spec': {
                'containers': [{
                    'image': 'flowd',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'flowd',
                    'ports': [{'containerPort': 9001}, {'containerPort': 9002}],
                    'env': [
                        {'name': 'ETCD_HOST', 'value': etcd_host},
                        {
                            'name': 'KAFKA_HOST',
                            'value': DEV_KAFKA_HOST if kafka_enabled else None
                        },
                        {'name': 'REXFLOW_XGW_IMAGE', 'value': DEFAULT_XGW_IMAGE},
                        {'name': 'REXFLOW_CATCH_IMAGE', 'value': DEFAULT_CATCH_IMAGE},
                        {'name': 'REXFLOW_THROW_IMAGE', 'value': DEFAULT_THROW_IMAGE},
                        {'name': 'REXFLOW_VERSION', 'value': DEFAULT_REXFLOW_VERSION},
                        {'name': 'REXFLOW_IS_PRODUCTION', 'value': 'False'},
                    ]
                }],
                'serviceAccountName': 'flowd'}
        }
    }
}

flowd_edit_default_spec = {
    'apiVersion': 'rbac.authorization.k8s.io/v1',
    'kind': 'RoleBinding',
    'metadata': {'name': 'flowd-edit-default', 'namespace': 'default'},
    'subjects': [
        {
            'kind': 'ServiceAccount',
            'name': 'flowd',
            'namespace': 'rexflow'
        }
    ],
    'roleRef': {
        'kind': 'ClusterRole',
        'name': 'edit',
        'apiGroup': 'rbac.authorization.k8s.io'
    }
}

rexflow_gateway_spec = {
    'apiVersion': 'networking.istio.io/v1alpha3',
    'kind': 'Gateway',
    'metadata': {'name': 'rexflow-gateway'},
    'spec': {
        'selector': {'istio': 'ingressgateway'},
        'servers': [
            {'port': {'number': 80, 'name': 'http', 'protocol': 'HTTP'},
             'hosts': ['*']},
        ],
    },
}

flowd_virtual_service_spec = {
    'apiVersion': 'networking.istio.io/v1alpha3',
    'kind': 'VirtualService',
    'metadata': {'name': 'flowd'},
    'spec': {
        'hosts': ['*'],
        'gateways': ['rexflow-gateway'],
        'http': [
            {
                'match': [{'uri': {'prefix': '/flowd'}}],
                'rewrite': {'uri': '/'},
                'route': [{'destination': {'port': {'number': 9002},
                                           'host': 'flowd'}}],
            },
            {
                'match': [{'authority': {'regex': 'flowd.*[:]9001'}}],
                'route': [{'destination': {'port': {'number': 9001},
                                           'host': 'flowd'}}],
            },
        ],
    },
}

healthd_service_acct_spec = {
    'apiVersion': 'v1',
    'kind': 'ServiceAccount',
    'metadata': {'name': 'healthd', 'namespace': 'rexflow'}
}

healthd_service_spec = {
    'apiVersion': 'v1',
    'kind': 'Service',
    'metadata': {
        'labels': {'app': 'healthd'},
        'name': 'healthd',
        'namespace': 'rexflow',
    },
    'spec': {
        'ports': [{'name': 'http', 'port': 5050, 'targetPort': 5050}],
        'selector': {'app': 'healthd'},
    },
}

mk_healthd_deployment_spec = lambda etcd_host, kafka_enabled: {  # noqa
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': 'healthd'},
    'spec': {
        'replicas': 1,
        'selector': {'matchLabels': {'app': 'healthd'}},
        'template': {
            'metadata': {'labels': {'app': 'healthd'}},
            'spec': {
                'containers': [
                    {
                        'image': 'healthd',
                        'imagePullPolicy': 'IfNotPresent',
                        'name': 'healthd',
                        'ports': [{'containerPort': 5050}],
                        'env': [
                            {
                            'name': 'KAFKA_HOST',
                            'value': 'my-cluster-kafka-bootstrap.kafka:9092' if kafka_enabled \
                                else None
                            },
                            {'name': 'ETCD_HOST', 'value': etcd_host},
                            {'name': 'HEALTHD_ON_KUBERNETES', 'value': 'True'}
                        ],
                    },
                ],
                'serviceAccountName': 'healthd'}
        },
    },
}

healthd_virtual_service_spec = {
    'apiVersion': 'networking.istio.io/v1alpha3',
    'kind': 'VirtualService',
    'metadata': {'name': 'healthd'},
    'spec': {
        'hosts': ['*'],
        'gateways': ['rexflow-gateway'],
        'http': [
            {
                'match': [{'uri': {'prefix': '/healthd'}}],
                'rewrite': {'uri': '/'},
                'route': [
                    {
                        'destination': {
                            'port': {'number': 5050},
                            'host': 'healthd.rexflow.svc.cluster.local'},
                    },
                ],
            },
        ],
    },
}

healthd_edit_default_spec = {
    'apiVersion': 'rbac.authorization.k8s.io/v1',
    'kind': 'RoleBinding',
    'metadata': {'name': 'healthd-edit-default', 'namespace': 'default'},
    'subjects': [
        {
            'kind': 'ServiceAccount',
            'name': 'healthd',
            'namespace': 'rexflow'
        }
    ],
    'roleRef': {
        'kind': 'ClusterRole',
        'name': 'edit',
        'apiGroup': 'rbac.authorization.k8s.io'
    }
}
