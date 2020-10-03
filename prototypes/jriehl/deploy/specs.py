rexflow_namespace_spec = {
    'apiVersion': 'v1',
    'kind': 'Namespace',
    'metadata': {'name': 'rexflow'}
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

mk_flowd_deployment_spec = lambda etcd_host : {
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': 'flowd'},
    'spec': {
        'replicas': 1,
        'selector': {'matchLabels': {'app': 'flowd'}},
        'template': {
            'metadata': {'labels': {'app': 'flowd'}},
            'spec': {
                'containers': [
                    {'image': 'flowd',
                     'imagePullPolicy': 'IfNotPresent',
                     'name': 'flowd',
                     'ports': [{'containerPort': 9001}, {'containerPort': 9002}],
                     'env': [{'name': 'ETCD_HOST', 'value': etcd_host}]}
                ],
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

mk_healthd_deployment_spec = lambda etcd_host: {
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
                    {'image': 'healthd',
                     'imagePullPolicy': 'IfNotPresent',
                     'name': 'healthd',
                     'ports': [{'containerPort': 5050}],
                     'env': [{'name': 'ETCD_HOST', 'value': etcd_host}]}
                ],
                'serviceAccountName': 'healthd'}
        }
    }
}
