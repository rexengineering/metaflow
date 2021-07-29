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
        config['spec']['template']['spec']['containers'][0]['env'].append({
            'name': 'DEFAULT_NOTIFICATION_KAFKA_TOPIC',
            'value': "rexflow-all-traffic" if kafka_enabled else None
        })
        config['spec']['template']['spec']['containers'][0]['env'].append({
            'name': 'REXFLOW_POSTGRES_DB_URI',
            'value': 'postgresql://postgresadmin:admin123@postgres.rexflow:5432/postgresdb' if kafka_enabled else None
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
        'replicas': 1, 
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

rexflow_db_constructor_vs = {
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
                            },
                            {
                                'name': "REXFLOW_POSTGRES_DB_URI",
                                "value": 'postgresql://postgresadmin:admin123@postgres.rexflow:5432/postgresdb',
                            },
                            {
                                'name': 'DEFAULT_NOTIFICATION_KAFKA_TOPIC',
                                'value': 'rexflow-all-traffic',
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
prometheus_cluster_role = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRole', 'metadata': {'creationTimestamp': None, 'name': 'prometheus'}, 'rules': [{'apiGroups': [''], 'resources': ['nodes', 'nodes/metrics', 'services', 'endpoints', 'pods'], 'verbs': ['get', 'list', 'watch']}, {'apiGroups': [''], 'resources': ['configmaps'], 'verbs': ['get']}, {'apiGroups': ['networking.k8s.io'], 'resources': ['ingresses'], 'verbs': ['get', 'list', 'watch']}, {'nonResourceURLs': ['/metrics'], 'verbs': ['get']}]}
prometheus_cluster_role_binding = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRoleBinding', 'metadata': {'name': 'prometheus'}, 'roleRef': {'apiGroup': 'rbac.authorization.k8s.io', 'kind': 'ClusterRole', 'name': 'prometheus'}, 'subjects': [{'kind': 'ServiceAccount', 'name': 'prometheus', 'namespace': 'default'}]}
#flowd_monitor = {'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'ServiceMonitor', 'metadata': {'name': 'flowd', 'labels': {'app': 'flowd'}}, 'spec': {'selector': {'matchLabels': {'app': 'flowd'}}, 'endpoints': [{'port': 'http'}]}}
prometheus = {'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'Prometheus', 'metadata': {'name': 'prometheus'}, 'spec': {'serviceAccountName': 'prometheus', 'serviceMonitorSelector': {'matchLabels': {'app': 'flowd'}}, 'resources': {'requests': {'memory': '400Mi'}}, 'enableAdminAPI': False}}
prometheus_service_account = {'apiVersion': 'v1', 'kind': 'ServiceAccount', 'metadata': {'name': 'prometheus'}}
prometheus_service = {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': 'prometheus', 'labels': {'app': 'prometheus'}}, 'spec': {'ports': [{'name': 'web', 'port': 9090, 'targetPort': 'web'}], 'selector': {'app': 'prometheus'}, 'sessionAffinity': 'ClientIP'}}
grafana_pvc = {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim', 'metadata': {'name': 'grafana-pvc'}, 'spec': {'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '1Gi'}}}}
grafana_deployment = {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'labels': {'app': 'grafana'}, 'name': 'grafana'}, 'spec': {'selector': {'matchLabels': {'app': 'grafana'}}, 'template': {'metadata': {'labels': {'app': 'grafana'}}, 'spec': {'securityContext': {'fsGroup': 472, 'supplementalGroups': [0]}, 'containers': [{'name': 'grafana', 'image': 'grafana/grafana:7.5.2', 'imagePullPolicy': 'IfNotPresent', 'ports': [{'containerPort': 3000, 'name': 'http-grafana', 'protocol': 'TCP'}], 'readinessProbe': {'failureThreshold': 3, 'httpGet': {'path': '/robots.txt', 'port': 3000, 'scheme': 'HTTP'}, 'initialDelaySeconds': 10, 'periodSeconds': 30, 'successThreshold': 1, 'timeoutSeconds': 2}, 'livenessProbe': {'failureThreshold': 3, 'initialDelaySeconds': 30, 'periodSeconds': 10, 'successThreshold': 1, 'tcpSocket': {'port': 3000}, 'timeoutSeconds': 1}, 'resources': {'requests': {'cpu': '250m', 'memory': '750Mi'}}, 'volumeMounts': [{'mountPath': '/var/lib/grafana', 'name': 'grafana-pv'}]}], 'volumes': [{'name': 'grafana-pv', 'persistentVolumeClaim': {'claimName': 'grafana-pvc'}}]}}}}
grafana_svc = {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': 'grafana'}, 'spec': {'ports': [{'port': 3000, 'protocol': 'TCP', 'targetPort': 'http-grafana'}], 'selector': {'app': 'grafana'}, 'sessionAffinity': 'None', 'type': 'LoadBalancer'}}
flowd_monitor = {'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'ServiceMonitor', 'metadata': {'name': 'prometheus', 'labels': {'app': 'flowd'}}, 'spec': {'endpoints': [{'interval': '30s', 'port': 'http'}], 'selector': {'matchLabels': {'app': 'flowd'}}}}
flowd_grpc_monitor = {'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'ServiceMonitor', 'metadata': {'name': 'prometheus-grpc', 'labels': {'app': 'flowd'}}, 'spec': {'endpoints': [{'interval': '30s', 'targetPort': 9001}], 'selector': {'matchLabels': {'app': 'flowd'}}}}