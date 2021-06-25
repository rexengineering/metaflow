import logging

import kubernetes.client
import kubernetes.client.rest
import os
import subprocess

from . import specs


def wrap_api_call(api_call):
    def _wrapped_api_call(*args, **kws):
        result = None
        try:
            result = api_call(*args, **kws)
        except kubernetes.client.rest.ApiException as exn:
            # a 404 usually indicates that istio is not active on the k8s cluster
            if exn.status == 404:
                logging.error('\n***\nIs istio installed? istioctl install --set profile=demo\n***')
            logging.exception(exn)
        return result
    return _wrapped_api_call


class Deployer:
    def __init__(self):
        self.core_v1 = kubernetes.client.CoreV1Api()
        self.create_namespace = wrap_api_call(self.core_v1.create_namespace)
        self.delete_namespace = wrap_api_call(self.core_v1.delete_namespace)
        self.create_namespaced_service_account = wrap_api_call(
            self.core_v1.create_namespaced_service_account)
        self.delete_namespaced_service_account = wrap_api_call(
            self.core_v1.delete_namespaced_service_account)
        self.create_namespaced_service = wrap_api_call(
            self.core_v1.create_namespaced_service)
        self.delete_namespaced_service = wrap_api_call(
            self.core_v1.delete_namespaced_service)
        self.apps_v1 = kubernetes.client.AppsV1Api()
        self.create_namespaced_deployment = wrap_api_call(
            self.apps_v1.create_namespaced_deployment)
        self.delete_namespaced_deployment = wrap_api_call(
            self.apps_v1.delete_namespaced_deployment)
        self.rbac_v1 = kubernetes.client.RbacAuthorizationV1Api()
        self.create_namespaced_role_binding = wrap_api_call(
            self.rbac_v1.create_namespaced_role_binding)
        self.delete_namespaced_role_binding = wrap_api_call(
            self.rbac_v1.delete_namespaced_role_binding)
        self.custom_api = kubernetes.client.CustomObjectsApi()
        self.create_namespaced_custom_object = wrap_api_call(
            self.custom_api.create_namespaced_custom_object)
        self.delete_namespaced_custom_object = wrap_api_call(
            self.custom_api.delete_namespaced_custom_object)
        self.create_namespaced_config_map    = wrap_api_call(
            self.core_v1.create_namespaced_config_map)
        self.create_namespaced_persistent_volume_claim = wrap_api_call(
            self.core_v1.create_namespaced_persistent_volume_claim)
        self.delete_namespaced_config_map    = wrap_api_call(
            self.core_v1.delete_namespaced_config_map)
        self.delete_namespaced_persistent_volume_claim  = wrap_api_call(
            self.core_v1.delete_namespaced_persistent_volume_claim)
        self.create_persistent_volume        = wrap_api_call(
            self.core_v1.create_persistent_volume)
        self.delete_persistent_volume        = wrap_api_call(
            self.core_v1.delete_persistent_volume)

    def create(self, namespace):
        print("The deploy module is used for dev deployments. As such, we are now "
              "setting the kube context to docker-desktop.", flush=True)
        subprocess.check_output("kubectl config use-context docker-desktop".split())
        self.create_namespace(specs.rexflow_namespace_spec)

        # ETCD
        self.create_namespaced_service_account(
            'rexflow', specs.etcd_service_acct_spec)
        self.create_namespaced_service(
            'rexflow', specs.etcd_service_specs)
        self.create_namespaced_deployment(
            'rexflow', specs.etcd_deployment_spec)
        # flowd 
        self.create_namespaced_service_account(
            'rexflow', specs.flowd_service_acct_spec)
        self.create_namespaced_service(
            'default', specs.flowd_service_specs['default'])
        self.create_namespaced_service(
            'rexflow', specs.flowd_service_specs['rexflow'])
        self.create_namespaced_deployment(
            'rexflow', specs.mk_flowd_deployment_spec('rexflow-etcd.rexflow',
            namespace.kafka
        ))
        self.create_namespaced_role_binding(
            'default', specs.flowd_edit_default_spec)

        # healthd
        self.create_namespaced_service_account(
            'rexflow', specs.healthd_service_acct_spec)
        self.create_namespaced_service(
            'rexflow', specs.healthd_service_spec)
        self.create_namespaced_deployment(
            'rexflow', specs.mk_healthd_deployment_spec('rexflow-etcd.rexflow',
            namespace.kafka
        ))
        self.create_namespaced_role_binding(
            'default', specs.healthd_edit_default_spec)

        # rex-flow-constructor
        self.create_namespaced_persistent_volume_claim(
            'rexflow', specs.postgres_pvc)
        self.create_persistent_volume(
            specs.postgres_pv)
        self.create_namespaced_config_map(
            'rexflow', specs.postgres_configmap )
        self.create_namespaced_service(
            'rexflow', specs.postgres_service)
        self.create_namespaced_deployment(
            'rexflow', specs.postgres_deployment)
        
        # rexflow_db_constructor
        self.create_namespaced_service(
            'rexflow', specs.rexflow_db_constructor_svc)
        self.create_namespaced_deployment(
            'rexflow', specs.rexflow_db_constructor_deployment)
        self.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'rexflow', 'gateways',
            specs.rexflow_db_constructor_gateway)
        self.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'rexflow', 'virtualservices',
            specs.rexflow_db_constructor_vs)

        # Gateway and virtual services
        self.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'gateways',
            specs.rexflow_gateway_spec)
        self.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            specs.flowd_virtual_service_spec)
        self.create_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            specs.healthd_virtual_service_spec)
        

        if namespace.kafka:
            os.system("kubectl create ns kafka")
            os.system("kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka")
            os.system("kubectl create -f "
                "https://strimzi.io/examples/latest/kafka/kafka-persistent-single.yaml -n kafka ")

    def delete(self, namespace):
        print("The deploy module is used for dev deployments. As such, we are now "
              "setting the kube context to docker-desktop.", flush=True)
        subprocess.check_output("kubectl config use-context docker-desktop".split())
        self.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            'healthd')
        self.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'virtualservices',
            'flowd')
        self.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'default', 'gateways',
            'rexflow-gateway')
        # rexflow-constructor delete
        self.delete_namespaced_deployment('rexflow-db-constructor', 'rexflow')
        self.delete_namespaced_service('rexflow-db-constructor' ,'rexflow')
        self.delete_namespaced_custom_object(
            'networking.istio.io', 'v1alpha3', 'rexflow', 'gateways',
            'rexflow-db-constructor')
        self.delete_namespaced_custom_object(
        'networking.istio.io', 'v1alpha3', 'rexflow', 'virtualservices',
        'rexflow-db-constructor')
        # postgres delete
        self.delete_namespaced_deployment('postgres', 'rexflow')
        self.delete_namespaced_service('postgres', 'rexflow')
        self.delete_namespaced_config_map('postgres', 'rexflow')
        self.delete_namespaced_persistent_volume_claim('postgres', 'rexflow')
        self.delete_persistent_volume('postgres')
        self.delete_namespaced_service('flowd', 'default')
        self.delete_namespaced_service('flowd', 'rexflow')
        self.delete_namespaced_deployment('flowd', 'rexflow')
        self.delete_namespaced_service('healthd', 'rexflow')
        self.delete_namespaced_deployment('healthd', 'rexflow')
        self.delete_namespaced_role_binding('flowd-edit-default', 'default')
        self.delete_namespaced_role_binding('healthd-edit-default', 'default')
        self.delete_namespaced_service_account('healthd', 'rexflow')
        self.delete_namespaced_service_account('flowd', 'rexflow')
        self.delete_namespaced_service('rexflow-etcd', 'rexflow')
        self.delete_namespaced_deployment('rexflow-etcd', 'rexflow')
        self.delete_namespaced_service_account('rexflow-etcd', 'rexflow')
        self.delete_namespace('rexflow')

        if namespace.kafka:
            os.system("kubectl delete -f "
                    "https://strimzi.io/examples/latest/kafka/kafka-persistent-single.yaml -n kafka ")
            os.system("kubectl delete -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka")
            os.system("kubectl delete ns kafka")
