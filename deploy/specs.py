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

def mk_flowd_deployment_spec(etcd_host, kafka_enabled):
    config = {
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
                            {"name": "I_AM_FLOWD", "value": "True"},
                            {
                                "name": "REXFLOW_FLOWD_HOST",
                                "value": "flowd.rexflow",
                            },
                            {
                                "name": "REXFLOW_FLOWD_PORT",
                                "value": "9002",
                            },
                        ]
                    }],
                    'serviceAccountName': 'flowd'}
            }
        }
    }
    if kafka_enabled:
        config['spec']['template']['spec']['containers'][0]['env'].append({
            'name': 'REXFLOW_KAFKA_HOST',
            'value': DEV_KAFKA_HOST if kafka_enabled else None
        })
    return config

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

def mk_healthd_deployment_spec(etcd_host, kafka_enabled):
    config = {
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
                                {'name': 'ETCD_HOST', 'value': etcd_host},
                                {
                                    "name": "REXFLOW_FLOWD_HOST",
                                    "value": "flowd.rexflow",
                                },
                                {
                                    "name": "REXFLOW_FLOWD_PORT",
                                    "value": "9002",
                                },
                                {'name': 'HEALTHD_ON_KUBERNETES', 'value': 'True'}
                            ],
                        },
                    ],
                    'serviceAccountName': 'healthd'}
            },
        },
    }
    if kafka_enabled:
        config['spec']['template']['spec']['containers'][0]['env'].append({
            'name': 'REXFLOW_KAFKA_HOST',
            'value': DEV_KAFKA_HOST if kafka_enabled else None
        })
    return config

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

postgres_deployment = {
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'creationTimestamp': None, 
    'labels': {'app': 'postgres'}, 
    'name': 'postgres'}, 
    'spec': {
        'progressDeadlineSeconds': 2147483647, 
        'replicas': 1, 
        'revisionHistoryLimit': 2147483647, 
        'selector': {
            'matchLabels': {
                'app': 'postgres'}}, 
        'strategy': {
            'rollingUpdate': {
                'maxSurge': 1, 
                'maxUnavailable': 1
            }, 
            'type': 'RollingUpdate'
        }, 
        'template': {
            'metadata': {
                'creationTimestamp': None, 
                'labels': {'app': 'postgres'}}, 
            'spec': {
                'containers': [
                    {
                        'envFrom': [
                            {
                                'configMapRef': {'name': 'postgres'}
                            }], 
                        'image': 'postgres:10.4', 
                        'imagePullPolicy': 'IfNotPresent', 
                        'name': 'postgres', 
                        'ports': [
                             {
                                 'containerPort': 5432, 
                                 'protocol': 'TCP'
                             }], 
                        'resources': {}, 
                        'terminationMessagePath': '/dev/termination-log', 
                        'terminationMessagePolicy': 'File', 
                        'volumeMounts': [
                            {
                                'mountPath': '/var/lib/postgresql/data', 
                                'name': 'postgredb'
                            }
                        ]
                    }
                ], 
                        'dnsPolicy': 'ClusterFirst', 
                        'restartPolicy': 'Always', 
                        'schedulerName': 'default-scheduler', 
                        'securityContext': {}, 
                        'terminationGracePeriodSeconds': 30, 
                        'volumes': [
                            {'name': 'postgredb', 
                            'persistentVolumeClaim': {
                                'claimName': 'postgres'
                                }
                            }
                        ]
                        }
                    }
                }
            }

postgres_configmap  = {
    'apiVersion': 'v1', 
    'kind': 'ConfigMap', 
    'metadata': {
        'name': 'postgres', 
        'labels': {
            'app': 'postgres'}
            }, 
        'data': {
            'POSTGRES_DB': 'postgresdb', 
            'POSTGRES_USER': 'postgresadmin', 
            'POSTGRES_PASSWORD': 'admin123'
            }
        }

postgres_service    = {
    'apiVersion': 'v1', 
    'kind': 'Service', 
    'metadata': {
        'name': 'postgres', 
        'labels': {
            'app': 'postgres'
            }
        }, 
    'spec': {
        'type': 'NodePort', 
        'ports': [
            {
                'port': 5432
                }
            ], 
            'selector': {
                'app': 'postgres'
                }
            }
        }

postgres_pv    = {
    'kind': 'PersistentVolume', 
    'apiVersion': 'v1', 
    'metadata': {
        'name': 'postgres', 
        'labels': {
            'type': 'local', 
            'app': 'postgres'
            }
        }, 
    'spec': {
        'storageClassName': 'manual', 
        'capacity': {
            'storage': '5Gi'
        }, 
        'accessModes': ['ReadWriteMany'], 
        'hostPath': {
            'path': '/mnt/data'
            }
        }
    }

postgres_pvc   = {
    'kind': 'PersistentVolumeClaim', 
    'apiVersion': 'v1', 
    'metadata': {
        'name': 'postgres', 
        'labels': {
            'app': 'postgres'
            }
        }, 
    'spec': {
        'storageClassName': 'manual', 
        'accessModes': ['ReadWriteMany'], 
        'resources': {
            'requests': 
            {'storage': '5Gi'}
            }
        }
    }

rexflow_db_constructor_vc = {
    'apiVersion': 'networking.istio.io/v1alpha3', 
    'kind': 'VirtualService', 
    'metadata': {
        'name': 'rexflow-db-constructor' 
        }, 
    'spec': {
        'hosts': ['*'], 
        'gateways': ['rexflow-db-constructor'], 
        'http': [
            {
                'match': [
                    {
                        'uri': {'prefix': '/rexflow-db-constructor'}
                    }
                ], 
                'rewrite': {
                    'uri': '/'
                    }, 
                'route': [
                    {
                        'destination': {
                            'port': {'number': 5000}, 
                            'host': 'rexflow-db-constructor'}
                            }
                        ]
                    }
                ]
            }
        }

rexflow_db_constructor_svc = {
    'apiVersion': 'v1', 
    'kind': 'Service', 
    'metadata': {
        'name': 'rexflow-db-constructor', 
        'labels': {
            'app': 'rexflow-db-constructor'
            }
        }, 
        'spec': {
            'ports': [
                {
                    'port': 5000, 
                    'protocol': 'TCP'
                }
            ], 
            'selector': {
                'app': 
                'rexflow-db-constructor'
                }
            }
        }

rexflow_db_constructor_gateway = {
    'apiVersion': 'networking.istio.io/v1alpha3', 
    'kind': 'Gateway', 
    'metadata': {
        'name': 'rexflow-db-constructor'
                }, 
    'spec': {
        'selector': {
            'istio': 'ingressgateway'}, 
            'servers': [
                {
                    'port': {
                        'number': 80, 
                        'name': 'http', 
                        'protocol': 'HTTP'
                        }, 
                    'hosts': ['*']
                }
            ]
        }
    }
    
rexflow_db_constructor_deployment = {
    'apiVersion': 'apps/v1', 
    'kind': 'Deployment', 
    'metadata': {
        'name': 'rexflow-db-constructor',
        'labels': {
            'app': "rexflow-db-constructor",
        }
    }, 
    'spec': {
        'selector': {
            'matchLabels': {
                'app': 'rexflow-db-constructor'
                            }
                }, 
        'replicas': 1, 
        'template': {
            'metadata': 
            {
                'labels': {
                    'app': 'rexflow-db-constructor'
                    }
            }, 
            'spec': {
                'containers': [
                    {
                        'name': 'hellothere', 
                        'image': 'rexflow-db-manager', 
                        'imagePullPolicy': 'Never', 
                        'env': [
                            {
                                'name': 'REXFLOW_KAFKA_HOST', 
                                'value': 'my-cluster-kafka-bootstrap.kafka:9092'
                            }
                        ], 
                        'ports': [
                            {
                                'containerPort': 5000
                            }
                        ]
                    }
                ]
            }
        }
    }
}