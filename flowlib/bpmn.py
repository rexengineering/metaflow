"""Utility library for working with BPMN documents.
"""

from collections import OrderedDict
from io import IOBase, StringIO, BytesIO
import functools
import hashlib
import json
import logging
import os
import subprocess
import sys
from typing import Mapping, Set, List

import boto3
from botocore.exceptions import ClientError
import yaml
import xmltodict

from .etcd_utils import get_etcd
from .task import BPMNTask
from .exclusive_gateway import BPMNXGateway
from .parallel_gateway import BPMNParallelGateway
from .start_event import BPMNStartEvent
from .end_event import BPMNEndEvent
from .throw_event import BPMNThrowEvent
from .catch_event import BPMNCatchEvent
from .constants import WorkflowKeys, to_valid_k8s_name
from .user_task import BPMNUserTask

from .bpmn_util import (
    HealthProperties,
    iter_xmldict_for_key,
    raw_proc_to_digraph,
    BPMNComponent,
    WorkflowProperties,
    ServiceProperties,
    CallProperties,
    outgoing_sequence_flow_table,
)
from .k8s_utils import (
    add_labels,
    create_deployment,
    create_rexflow_ingress_vs,
    create_service,
    create_serviceaccount,
    get_rexflow_labels,
    add_annotations,
    get_rexflow_component_annotations,
)
from .config import (
    DO_MANUAL_INJECTION,
    K8S_SPECS_S3_BUCKET,
    UI_BRIDGE_IMAGE,
    UI_BRIDGE_NAME,
    UI_BRIDGE_PORT,
    UI_BRIDGE_INIT_PATH,
    WORKFLOW_PUBLISHER_LISTEN_PORT,
    WORFKLOW_PUBLISHER_IMAGE,
    CREATE_DEV_INGRESS,
    PASSTHROUGH_IMAGE,
)


ISTIO_VERSION = os.getenv('ISTIO_VERSION', '1.8.2')
REX_ISTIO_PROXY_IMAGE = os.getenv('REX_ISTIO_PROXY_IMAGE', 'rex-proxy:1.8.2')


class BPMNProcess:
    def __init__(self, process: OrderedDict):
        self._process = process
        self.hash = hashlib.sha256(json.dumps(self._process).encode()).hexdigest()[:8]
        self.entry_points = [entry_point for entry_point in iter_xmldict_for_key(self._process, 'bpmn:startEvent')]
        assert len(self.entry_points) > 0, "Must have at least one StartEvent."

        # TODO: figure out how to do annotations on multiple start events
        # annotations = list(get_annotations(process, self.entry_points[0]['@id']))
        all_annotations = iter_xmldict_for_key(self._process, 'bpmn:textAnnotation')
        global_annotations = [
            yaml.safe_load(annot['bpmn:text'].replace('\xa0', ''))
            for annot in all_annotations
            if annot['bpmn:text'].startswith('rexflow_global_properties')
        ]
        assert len(global_annotations) <= 1, "Can have at most one global rexflow annotation."

        self.annotation = global_annotations[0] if len(global_annotations) else None
        self.properties = WorkflowProperties(self.annotation)
        if not self.properties.id:
            self.properties.update({
                "id": to_valid_k8s_name(process['@id']),
            })

        # Put the hash in the id
        self.properties.update({
            'id_hash': self.hash,
            'id': f'{self.properties.id}-{self.hash}',
        })
        self.id = self.properties.id

        # needed for calculation of some BPMN Components
        self._digraph = raw_proc_to_digraph(process)
        self._sequence_flow_table = outgoing_sequence_flow_table(process)

        # Maps an Id (eg. "Event_25dst7" or "Gateway_2sh38s") to a BPMNComponent Object.
        self.component_map: Mapping[str, BPMNComponent] = {}

        # NOTE: As per `README.namespacing.md`, if we are in a shared namespace then we
        # append a small hash to the end of every k8s object in order to avoid conflicts.
        # The `id_hash` and `namespace_shared` have already been computed when we
        # created the WorkflowProperties object (see self.properties).

        # Now, create all of the BPMN Components.
        # Start with Tasks:
        self.tasks: List[BPMNTask] = []
        for task in iter_xmldict_for_key(process, 'bpmn:serviceTask'):
            bpmn_task = BPMNTask(task, process, self.properties)
            self.tasks.append(bpmn_task)
            self.component_map[task['@id']] = bpmn_task

        # Exclusive Gateways (conditional)
        self.xgateways: List[BPMNXGateway] = []
        for gw in iter_xmldict_for_key(process, 'bpmn:exclusiveGateway'):
            bpmn_gw = BPMNXGateway(gw, process, self.properties)
            self.xgateways.append(bpmn_gw)
            self.component_map[gw['@id']] = bpmn_gw

        # Parallel Gateways
        self.pgateways: List[BPMNParallelGateway] = []
        for gw in iter_xmldict_for_key(process, 'bpmn:parallelGateway'):
            bpmn_gw = BPMNParallelGateway(gw, process, self.properties)
            self.pgateways.append(bpmn_gw)
            self.component_map[gw['@id']] = bpmn_gw

        # Don't forget BPMN Start Event!
        self.start_events: List[BPMNStartEvent] = []
        for entry_point in self.entry_points:
            bpmn_start_event = BPMNStartEvent(entry_point, process, self.properties)
            self.start_events.append(bpmn_start_event)
            # equivalent to:
            # self.component_map[bpmn_start_even.id] = bpmn_start_event
            self.component_map[entry_point['@id']] = bpmn_start_event

        # Don't forget BPMN End Events!
        self.end_events: List[BPMNEndEvent] = []
        for eev in iter_xmldict_for_key(process, 'bpmn:endEvent'):
            end_event = BPMNEndEvent(eev, process, self.properties)
            self.end_events.append(end_event)
            self.component_map[eev['@id']] = end_event

        # Throw Events.
        self.throws: List[BPMNThrowEvent] = []
        for event in iter_xmldict_for_key(process, 'bpmn:intermediateThrowEvent'):
            assert 'bpmn:incoming' in event, "Must have incoming edge to Throw Event."
            bpmn_throw = BPMNThrowEvent(event, process, self.properties)
            self.throws.append(bpmn_throw)
            self.component_map[event['@id']] = bpmn_throw

        self.catches: List[BPMNCatchEvent] = []
        for event in iter_xmldict_for_key(process, 'bpmn:intermediateCatchEvent'):
            bpmn_catch = BPMNCatchEvent(event, process, self.properties)
            self.catches.append(bpmn_catch)
            self.component_map[event['@id']] = bpmn_catch

        # User tasks are a bit of an odd duck. Normally, we go by the following rules:
        # 1. One BPMNComponent object per component on the bpmn diagram
        # 2. One k8s service/deployment or `EnvoyFilter` per component on the bpmn diagram
        # However, for any Workflow with one or more User Tasks, we deploy ONE UI-Bridge.
        # So that means two things:
        # 1. While we have multiple BPMNUserTask objects, they will all share the same
        #    ServiceProperties and CallProperties objects.
        # 2. The k8s specs are generated in this file by the BPMNComponent class, not in
        #    the .to_kubernetes() method of the BPMNUserTask.
        # Essentially, the BPMNUserTask object is just used for bookkeeping.
        self.user_task_definitions = [defn for defn in iter_xmldict_for_key(process, 'bpmn:userTask')]
        if len(self.user_task_definitions):
            self._ui_bridge_service_properties = ServiceProperties()

            # Important to do it this way, because then the id_hash is appropriately included or not
            # included in the k8s service name automagically.
            self._ui_bridge_service_properties.update({
                'host': UI_BRIDGE_NAME,
                'container': UI_BRIDGE_IMAGE,
                'port': UI_BRIDGE_PORT,
                'hash_used': (self.properties.namespace_shared),  # if in shared ns, use the hash
                'id_hash': self.properties.id_hash,
            })
            self._ui_bridge_call_properties = CallProperties()
            self._ui_bridge_call_properties.update({
                'path': UI_BRIDGE_INIT_PATH,
            })
        self.user_tasks: List[BPMNUserTask] = []
        for defn in self.user_task_definitions:
            bpmn_user_task = BPMNUserTask(
                defn, process, self.properties, self._ui_bridge_service_properties,
                self._ui_bridge_call_properties,
            )
            self.user_tasks.append(bpmn_user_task)
            self.component_map[defn['@id']] = bpmn_user_task

        self.all_components: List[BPMNComponent] = []
        self.all_components.extend(self.tasks)
        self.all_components.extend(self.xgateways)
        self.all_components.extend(self.pgateways)
        self.all_components.extend(self.throws)
        self.all_components.extend(self.catches)
        self.all_components.extend(self.end_events)
        self.all_components.extend(self.start_events)
        self.all_components.extend(self.user_tasks)

        # Check that there are no duplicate service names.
        all_names = set()
        for component in self.all_components:
            if component.name in all_names:
                assert False, f"Name {component.name} used twice! Not allowed."
            all_names.add(component.name)

        self._s3_bucket = None
        if K8S_SPECS_S3_BUCKET is not None:
            s3 = boto3.resource('s3')
            self._s3_bucket = s3.Bucket(K8S_SPECS_S3_BUCKET)
        else:
            logging.info("Not setting up s3 bucket for k8s specs: no bucket configured.")

    @property
    def kafka_topics(self):
        # Note: some kafka topics can only be determined at compile-time (i.e. when
        # to_kubernetes() is called) because they are dependent on the properties
        # of the edge between two nodes in the DAG. Therefore, we must refresh
        # the kafka_topics of the workflow.
        kafka_topics = []
        for component in self.all_components:
            # to_kubernetes() doesn't create any k8s resources; rather, it just
            # returns the specs AND updates the underlying BPMNComponent.kafka_topics
            # list.
            component.to_kubernetes(
                self.properties.id_hash,
                self.component_map,
                self._digraph,
                self._sequence_flow_table
            )
            kafka_topics.extend(component.kafka_topics)
        if self.properties.notification_kafka_topic:
            kafka_topics.append(self.properties.notification_kafka_topic)
        return set(kafka_topics)

    @classmethod
    def from_workflow_id(cls, workflow_id):
        etcd = get_etcd(is_not_none=True)
        process_xml = etcd.get(WorkflowKeys.proc_key(workflow_id))[0]
        process_dict = xmltodict.parse(process_xml)['bpmn:process']
        process = cls(process_dict)
        return process

    def to_xml(self):
        return xmltodict.unparse(OrderedDict([('bpmn:process', self._process)]))

    def to_digraph(self, digraph: dict = None):
        if digraph is None:
            digraph = dict()
        for sequence_flow in iter_xmldict_for_key(self._process, 'bpmn:sequenceFlow'):
            source_ref = sequence_flow['@sourceRef']
            target_ref = sequence_flow['@targetRef']
            if source_ref not in digraph:
                digraph[source_ref] = set()
            digraph[source_ref].add(target_ref)
        return digraph

    @property
    def namespace(self):
        return self.properties.namespace

    @property
    def namespace_shared(self):
        return self.properties.namespace_shared

    @property
    def digraph(self) -> Mapping[str, Set[str]]:
        if self._digraph is None:
            result = self.to_digraph()
            self._digraph = result
        else:
            result = self._digraph
        return result

    def to_kubernetes(self, stream: IOBase = None, id_hash: str = None, **kws):
        # No longer used
        raise NotImplementedError("REXFlow requires Istio.")

    def _save_specs_to_s3(self, specs, key):
        if not self._s3_bucket:
            logging.info("Not saving k8s specs to S3: No configured bucket.")
            return
        self._s3_bucket.upload_fileobj(BytesIO(specs.encode()), key)
        logging.info(f"Successfully saved k8s specs to S3 at {key}.")

    def _get_specs_from_s3(self, key):
        if not self._s3_bucket:
            logging.info("Not getting k8s specs from S3: No configured bucket.")
            return None
        fileobj = BytesIO()
        try:
            self._s3_bucket.download_fileobj(key, fileobj)
            logging.info(f"Getting k8s specs from S3 at {key}.")
            return fileobj.getvalue().decode()
        except ClientError:
            logging.info(f"Unable to download s3 object for {key}.")
            return None

    def to_istio(self, stream: IOBase = None, id_hash: str = None, **kws):
        if stream is None:
            stream = sys.stdout
        result = self.to_istio_helper(id_hash, **kws)
        if result is not None:
            stream.write(result)
        return result

    @functools.lru_cache
    def to_istio_helper(self, id_hash, **kws):
        # First, check if the input has been cached in s3. If so, then we retrieve and
        # do NOT recompute. This is critical so that we can update versions of flowd
        # without worrying about version conflicts.
        keys_obj = WorkflowKeys(self.properties.id)
        cached_result = self._get_specs_from_s3(keys_obj.specs)
        if cached_result:
            return cached_result

        results = []
        if not self.namespace_shared:
            results.append(
                {
                    'apiVersion': 'v1',
                    'kind': 'Namespace',
                    'metadata': {
                        'name': self.namespace,
                    },
                }
            )

        for bpmn_component in self.all_components:
            bpmn_component_specs = bpmn_component.to_kubernetes(
                id_hash, self.component_map, self._digraph, self._sequence_flow_table
            )

            # Annotate each k8s object with its task id.
            for spec in bpmn_component_specs:
                add_annotations(spec, get_rexflow_component_annotations(bpmn_component))
            results.extend(bpmn_component_specs)

        if len(self.user_tasks) > 0:
            logging.info('User tasks detected, adding UI bridge to deployment.')
            # TODO: Figure out configuration details for the UI bridge and add
            # to generated K8s specifications.
            ui_bridge_service_name = self._ui_bridge_service_properties.host

            bridge_config = {}
            for task in self.user_tasks:
                task_outbound_edges = set(self.digraph[task.id])
                task_outbound_components = [
                    self.component_map[component_id] for component_id in task_outbound_edges
                ]
                bridge_config[task.id] = [
                    {
                        'next_task_id_header': next_task.id,
                        'k8s_url': next_task.k8s_url,
                        'method': next_task.call_properties.method,
                    }
                    for next_task in task_outbound_components
                ]

            ui_bridge_env = [
                {
                    'name': 'WORKFLOW_DID',
                    'value': self.namespace
                },
                {
                    'name': 'WORKFLOW_TIDS',
                    'value': ':'.join([task.id for task in self.user_tasks]),
                },
                {
                    'name': 'BRIDGE_CONFIG',
                    'value': json.dumps(bridge_config),
                },
                {
                    'name': 'USE_SALESFORCE',
                    'value': self.properties._use_salesforce,
                },
                {
                    'name': 'SALESFORCE_PROFILE',
                    'value': '{"username":"ghester@rexhomes.com.qa1","consumer_key":"3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk","private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA/USE/o9vB/k6CEPm6sIjcPUiY0rw+jAhRiLJR1wUX9CuJ1+f\\nx/buK0Vqq59cm2bf1eWYIp0J6uqHG8A44xp89oXR6/DmJnJWBi8CRmyjRDNMpnIq\\nVgmjDuFXndKWkyHpyhgVtPIA3Bi+3UHQXbGX8E/rYXea28XQ7/HxybG9YHvJXZhn\\nBwqo8CmUFk+b7mjpwYd4i9cRsVtPDe9Mvf+1VWcGj+bWTAVFTGSjBknzCzJI3Yvh\\nAzhPYK3Zhxi7m/eWEYOPCYPRFxq7gijkaQq2szPYEq20N8r1pWgjXZPmCd/UQ0Ek\\nWHwGYrcmBPirO2/wpJJgQrhbTpMcsZTmw5v5dQIDAQABAoIBAE8TS6rnQbVtnS7j\\ndH+rqcEk6F20ElUrHdh2F/4Nw9a+owFsG8klUet0uv9mvFVQ42Y3Ty7PdT9Bhnml\\npJ1TsdyOn6JZDqLGZBF+L+mpFbi/g5kcYBeI3r5QoTiHfbfmiMYuiuh5/sa5ey49\\n1D7MqjG/4jAGVfV0Z+3izqk4s3Yh0RXU3KbYKVvJlPSAfiRsH8f/IvgIsux8bsCD\\n4+tEg2hBvLLlml9AIHC06S82w/xYBggXje550eMKtERl5bFlk+AIVYTo2bUzpFCX\\nWViv3JC7/6P6E/y6W4xSnaXLlvY+yeKotXkW0XReph/Q1TopI4rzF6VojlmSG3KB\\nCYo+EgECgYEA/8s+j9v54XqBYgozMVq17KcK8NGZFXWJDEeAHNN/DwblSRKTIDRb\\nLQp+H6OP6Rq/jWcQUDp35XwThSw5r6Lsv6Xa0yo2/05c58yCJxNvwIfduIs0emxQ\\nWc4JjP2o/2PbqLVLcFNIjw8jAg7+KGapRs1tC63MXsRQJArMPjsXZsECgYEA/XjB\\nDNgVGvvQK92m7hTCX+nuqx51mOGs1mSdhcCCnjCdwLwHQNQmG4zGPHjFjxeoUx6i\\nuYUFK2b8LJTLjbIWzqTBtiBtfY85XdpjR/SuFncYkHqQ0ms9c5jwA/2qb1IYfIHx\\nGPYov/m5MR3aBPuuPuUzQpwTWV6+HebPHQtwE7UCgYEAgoSSR5VWy1ZW7k+GD4jZ\\niwcw7fAEzI5Mf5d8JzlDe8do9wAjUitk2nagJESxCaA8XUpZaJZs1wuYajtGs/fO\\nFXvrTBQeO+cgQKZ5QrcILpUk7SUagd0CotAez3Ie6TFqw4q+E3Jrc5OlqUc9KCA5\\n/4aSPYNQ5IoG2l0oGhjMuAECgYEAzBgJSfBLvjh4vHlzSk0I3fYdKUgTZJCCfPbz\\nJ5mFEx8ORvyf0oGAVbqafGK6oKdp79PBLyR+rx3ze2osJOH7H1TmbWHbB7jldj68\\nplnMO2aWLu+h4OxcxNGmoXAFZjFyaf6vRWwgD8Ria7wfqteEzDv9dGr74YA6ERWi\\nOz7UdekCgYBslAlmMi8kmtx34GS+STe03xbiO9YtIs2/1qiYF1DQhlpJcDEC/Xtr\\n1UkbKUxLxAL8kL+9onIrUKM8Re3kdA/qFfiLCHpMBhmtUMA0unQQcY2QhXddyzFz\\n7Ts84zwHLQ0QpzTxiWO1j3TBJl59j1arhoB2ecnyT/tsULkR+h9YNQ==\\n-----END RSA PRIVATE KEY-----","domain":"test"}',
                },
            ]

            results.append(create_deployment(
                self.namespace,
                ui_bridge_service_name,
                UI_BRIDGE_IMAGE,
                UI_BRIDGE_PORT,
                ui_bridge_env,
                etcd_access=True,
                use_service_account=False,
                health_props=HealthProperties(),
            ))
            results.append(create_service(
                self.namespace,
                ui_bridge_service_name,
                UI_BRIDGE_PORT
            ))
            if CREATE_DEV_INGRESS:
                results.append(create_rexflow_ingress_vs(
                    self.namespace,
                    to_valid_k8s_name(f'{ui_bridge_service_name}-{self.namespace}'),
                    f'/{ui_bridge_service_name}-{self.namespace}',
                    UI_BRIDGE_PORT,
                    f'{UI_BRIDGE_NAME}.{self.namespace}.svc.cluster.local'
                ))

        if self.properties.passthrough_target is not None:
            results.extend(self._get_passthrough_services())

        if self.properties.notification_kafka_topic is not None:
            results.extend(self._get_workflow_publisher_specs())

        # Now, add the REXFlow labels
        for k8s_spec in results:
            add_labels(k8s_spec, get_rexflow_labels(self.properties.id))

        # This code below does manual sidecar injection. It is ONLY necessary
        # for dev on docker-desktop, since it is not easily feasible to
        # configure d4d istio to automatically inject a custom image.
        # On a true deployment (where we set imagePullSecrets), we
        # could easily tell Istio to automatically inject our own custom
        # proxy image, and thus remove the code below.
        temp_yaml = yaml.safe_dump_all(results, **kws)
        if not DO_MANUAL_INJECTION:
            self._save_specs_to_s3(temp_yaml, keys_obj.specs)
            return temp_yaml

        istioctl_result = subprocess.run(
            ['istioctl', 'kube-inject', '-f', '-'],
            input=temp_yaml, capture_output=True, text=True,
        )

        result = None

        if istioctl_result.returncode == 0:
            result = istioctl_result.stdout.replace(
                ': Always',
                ': IfNotPresent',
            ).replace(f'docker.io/istio/proxyv2:{ISTIO_VERSION}', REX_ISTIO_PROXY_IMAGE)
            self._save_specs_to_s3(result, keys_obj.specs)
        else:
            logging.error(f'Error from Istio:\n{istioctl_result.stderr}')

        return result

    def _get_workflow_publisher_specs(self):
        results = []
        env_config = [
            {
                "name": "REXFLOW_PUBLISHER_KAFKA_TOPIC",
                "value": self.properties.notification_kafka_topic,
            },
            {
                "name": "REXFLOW_PUBLISHER_WORKFLOW_ID",
                "value": self.properties.id,
            }
        ]
        results.append(create_deployment(
            self.namespace,
            self.properties.traffic_shadow_service_props.host,
            WORFKLOW_PUBLISHER_IMAGE,
            WORKFLOW_PUBLISHER_LISTEN_PORT,
            env_config,
            etcd_access=True,
            kafka_access=True,
            priority_class=self.properties.priority_class,
        ))
        results.append(create_service(
            self.namespace,
            self.properties.traffic_shadow_service_props.host,
            WORKFLOW_PUBLISHER_LISTEN_PORT,
        ))
        results.append(create_serviceaccount(
            self.namespace,
            self.properties.traffic_shadow_service_props.host,
        ))
        return results

    @property
    def xmldict(self) -> OrderedDict:
        return self._process

    def _get_passthrough_services(self):
        result = []

        # Maps from f"{service_name}.{namespace}"  --> list of url's for that service
        services = {}
        for task in self.tasks:
            if not task.is_passthrough:
                continue

            key = f'{task.service_name}.{task.namespace}'
            if key not in services:
                target_url = f'http://{task.service_name}'
                if self.properties.prefix_passthrough_with_namespace:
                    target_url += f'.{task.namespace}'
                target_url += '.' + self.properties.passthrough_target
                services[key] = {
                    'target_url': target_url,
                    'target_port': task._target_port,
                    'targets': [],
                    'service_name': task.service_name,
                    'namespace': task.namespace,
                    'service_port': task.service_properties.port,
                }

            services[key]['targets'].append({
                # TODO: See if this works with Gary's path templating.
                'path': task.call_properties.path.replace('{', '<').replace('}', '>'),
                'method': task.call_properties.method,
            })

        for service_key in services.keys():
            result.extend(self._generate_passthrough_service(services[service_key]))
        return result

    def _generate_passthrough_service(self, config):
        result = []
        service_name = config['service_name']
        target_port = config['target_port']
        namespace = config['namespace']
        service_port = config['service_port']

        env_config = [
            {
                'name': 'REXFLOW_PASSTHROUGH_CONFIG', 
                'value': json.dumps(config),
            },
        ]
        result.append(
            create_deployment(
                namespace,
                service_name,
                PASSTHROUGH_IMAGE,
                target_port,
                env_config,
                use_service_account=False,
                health_props=HealthProperties()
            )
        )
        result.append(
            create_serviceaccount(
                namespace,
                service_name,
            )
        )
        result.append(
            create_service(
                namespace,
                service_name,
                service_port,
                target_port,
            )
        )
        return result
