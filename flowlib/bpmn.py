'''Utility library for working with BPMN documents.
'''

from collections import OrderedDict
from io import IOBase, StringIO, BytesIO
import hashlib
import json
import logging
import os
import subprocess
import sys
from typing import Mapping, Set

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
from .constants import WorkflowKeys

from .bpmn_util import (
    iter_xmldict_for_key,
    raw_proc_to_digraph,
    get_annotations,
    BPMNComponent,
    WorkflowProperties,
    to_valid_k8s_name,
    outgoing_sequence_flow_table,
)
from .k8s_utils import (
    add_labels,
    get_rexflow_labels,
    add_annotations,
    get_rexflow_component_annotations,
)
from .config import DO_MANUAL_INJECTION, K8S_SPECS_S3_BUCKET


ISTIO_VERSION = os.getenv('ISTIO_VERSION', '1.8.2')
REX_ISTIO_PROXY_IMAGE = os.getenv('REX_ISTIO_PROXY_IMAGE', 'rex-proxy:1.8.2')


class BPMNProcess:
    def __init__(self, process: OrderedDict):
        self._process = process
        self.hash = hashlib.sha256(json.dumps(self._process).encode()).hexdigest()[:8]
        entry_point = process['bpmn:startEvent']
        assert isinstance(entry_point, OrderedDict), "Must have exactly one StartEvent."
        self.entry_point = entry_point
        annotations = list(get_annotations(process, self.entry_point['@id']))
        assert len(annotations) <= 1, "Must have only one annotation for start event."
        self.annotation = annotations[0] if len(annotations) else None
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
        self.component_map = {} # type: Mapping[str, BPMNComponent]

        # NOTE: As per `README.namespacing.md`, if we are in a shared namespace then we
        # append a small hash to the end of every k8s object in order to avoid conflicts.
        # The `id_hash` and `namespace_shared` have already been computed when we
        # created the WorkflowProperties object (see self.properties).

        # Now, create all of the BPMN Components.
        # Start with Tasks:
        self.tasks = []
        for task in iter_xmldict_for_key(process, 'bpmn:serviceTask'):
            bpmn_task = BPMNTask(task, process, self.properties)
            self.tasks.append(bpmn_task)
            self.component_map[task['@id']] = bpmn_task

        # Exclusive Gateways (conditional)
        self.xgateways = []
        for gw in iter_xmldict_for_key(process, 'bpmn:exclusiveGateway'):
            bpmn_gw = BPMNXGateway(gw, process, self.properties)
            self.xgateways.append(bpmn_gw)
            self.component_map[gw['@id']] = bpmn_gw

        # Parallel Gateways
        self.pgateways = []
        for gw in iter_xmldict_for_key(process, 'bpmn:parallelGateway'):
            bpmn_gw = BPMNParallelGateway(gw, process, self.properties)
            self.pgateways.append(bpmn_gw)
            self.component_map[gw['@id']] = bpmn_gw

        # Don't forget BPMN Start Event!
        self.start_event = BPMNStartEvent(self.entry_point, process, self.properties)
        self.component_map[self.entry_point['@id']] = self.start_event

        # Don't forget BPMN End Events!
        # TODO: Test to make sure it works with multiple End Events.
        self.end_events = []
        for eev in iter_xmldict_for_key(process, 'bpmn:endEvent'):
            end_event = BPMNEndEvent(eev, process, self.properties)
            self.end_events.append(end_event)
            self.component_map[eev['@id']] = end_event

        # Throw Events.
        # For now, to avoid forcing the user of REXFlow to have to annotate each event
        # as either a Throw or Catch, we will infer based on the following rule:
        # If there is an incoming edge to the Event in self.to_digraph, then
        # it's a Throw event. Else, it's a Catch event.
        self.throws = []
        for event in iter_xmldict_for_key(process, 'bpmn:intermediateThrowEvent'):
            assert 'bpmn:incoming' in event, "Must have incoming edge to Throw Event."
            bpmn_throw = BPMNThrowEvent(event, process, self.properties)
            self.throws.append(bpmn_throw)
            self.component_map[event['@id']] = bpmn_throw

        self.catches = []
        for event in iter_xmldict_for_key(process, 'bpmn:intermediateCatchEvent'):
            assert 'bpmn:incoming' not in event, "Can't have incoming edge to Catch Event."
            bpmn_catch = BPMNCatchEvent(event, process, self.properties)
            self.catches.append(bpmn_catch)
            self.component_map[event['@id']] = bpmn_catch

        self.all_components = []
        self.all_components.extend(self.tasks)
        self.all_components.extend(self.xgateways)
        self.all_components.extend(self.pgateways)
        self.all_components.extend(self.throws)
        self.all_components.extend(self.catches)
        self.all_components.extend(self.end_events)
        self.all_components.append(self.start_event)

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

        # First, check if the input has been cached in s3. If so, then we retrieve and
        # do NOT recompute. This is critical so that we can update versions of flowd
        # without worrying about version conflicts.
        keys_obj = WorkflowKeys(self.properties.id)
        cached_result = self._get_specs_from_s3(keys_obj.specs)
        if cached_result:
            stream.write(cached_result)
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

        for bpmn_component_id in self.component_map.keys():
            bpmn_component = self.component_map[bpmn_component_id]
            bpmn_component_specs = bpmn_component.to_kubernetes(
                id_hash, self.component_map, self._digraph, self._sequence_flow_table
            )

            # Annotate each k8s object with its task id.
            for spec in bpmn_component_specs:
                add_annotations(spec, get_rexflow_component_annotations(bpmn_component))
            results.extend(bpmn_component_specs)

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
            stream.write(temp_yaml)
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
            stream.write(result)
        else:
            logging.error(f'Error from Istio:\n{istioctl_result.stderr}')

        return result
