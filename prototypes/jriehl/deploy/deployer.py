import socket

import kubernetes.client

from . import specs

class Deployer:
    def __init__(self):
        self.core_v1 = kubernetes.client.CoreV1Api()
        self.apps_v1 = kubernetes.client.AppsV1Api()
        self.rbac_v1 = kubernetes.client.RbacAuthorizationV1Api()
        self.custom_api = kubernetes.client.CustomObjectsApi()

    def create(self, _):
        etcd_host = socket.getfqdn()
        self.core_v1.create_namespace(specs.rexflow_namespace_spec)
        self.core_v1.create_namespaced_service_account(
            'rexflow', specs.flowd_service_acct_spec)
        self.core_v1.create_namespaced_service(
            'default', specs.flowd_service_specs['default'])
        self.core_v1.create_namespaced_service(
            'rexflow', specs.flowd_service_specs['rexflow'])
        self.apps_v1.create_namespaced_deployment(
            'rexflow', specs.mk_flowd_deployment_spec(etcd_host))
        self.rbac_v1.create_namespaced_role_binding(
            'default', specs.flowd_edit_default_spec)
        self.core_v1.create_namespaced_service_account(
            'rexflow', specs.healthd_service_acct_spec)
        self.core_v1.create_namespaced_service(
            'rexflow', specs.healthd_service_spec)
        self.apps_v1.create_namespaced_deployment(
            'rexflow', specs.mk_healthd_deployment_spec(etcd_host))
        self.custom_api.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'gateways',
            specs.rexflow_gateway_spec)
        self.custom_api.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            specs.flowd_virtual_service_spec)
        self.custom_api.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            specs.healthd_virtual_service_spec)

    def delete(self, _):
        self.custom_api.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            'healthd')
        self.custom_api.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            'flowd')
        self.core_v1.delete_namespaced_service('flowd', 'default')
        self.core_v1.delete_namespaced_service('flowd', 'rexflow')
        self.apps_v1.delete_namespaced_deployment('flowd', 'rexflow')
        self.core_v1.delete_namespaced_service('healthd', 'rexflow')
        self.apps_v1.delete_namespaced_deployment('healthd', 'rexflow')
        self.rbac_v1.delete_namespaced_role_binding('flowd-edit-default', 'default')
        self.core_v1.delete_namespaced_service_account('healthd', 'rexflow')
        self.core_v1.delete_namespaced_service_account('flowd', 'rexflow')
        self.core_v1.delete_namespace('rexflow')
