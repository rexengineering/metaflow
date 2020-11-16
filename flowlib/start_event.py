'''
Implements BPMNStartEvent object, which for now is just a pass-through to Flowd.
'''

from collections import OrderedDict, namedtuple
from io import IOBase
import logging
import socket
import subprocess
import sys
from typing import Any, Iterator, List, Mapping, Optional, Set

import yaml
import xmltodict

from .envoy_config import get_envoy_config, Upstream
from .etcd_utils import get_etcd
from .bpmn_util import (
    iter_xmldict_for_key,
    CallProperties,
    ServiceProperties,
    HealthProperties,
    BPMNComponent,
)


class BPMNStartEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict, global_props):
        # Note: We don't call the super constructor.
        # TODO: separate this code out from Flowd
        self._namespace = global_props.namespace

    @property
    def health_properties(self) -> HealthProperties:
        raise "who goes there"

    @property
    def call_properties(self) -> CallProperties:
        raise "who goes there"

    @property
    def service_properties(self) -> ServiceProperties:
        raise "who goes there"

    @property
    def namespace(self) -> str:
        return self._namespace

    def to_kubernetes(self, id_hash, component_map: Mapping[str, BPMNComponent], digraph : OrderedDict) -> list:
        # Don't do anything since Flowd is already deployed.
        return []

    @property
    def k8s_url(self) -> str:
        '''Returns the fully-qualified host + path that is understood by the k8s
        kube-dns. For example, returns "http://my-service.my-namespace:my-port"
        '''
        # Need to override this since it's flowd.
        return "http://flowd.rexflow:9002"

    @property
    def path(self):
        return '/'

    @property
    def envoy_host(self) -> str:
        return "flowd.rexflow.svc.cluster.local"