'''
Implements BPMNEndEvent object, which for now is just a pass-through to Flowd.
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


class BPMNEndEvent(BPMNComponent):
    '''Wrapper for BPMN service task metadata.
    '''
    def __init__(self, task : OrderedDict, process : OrderedDict, global_props):
        # Note: We don't call the super constructor.
        # TODO: Separate this from Flowd.
        self._namespace = 'rexflow'
        self._health_properties = HealthProperties()
        self._call_properties = CallProperties()
        self._service_properties = ServiceProperties("flowd")
        self._service_properties.update({"host": "donezo!", "port": "9002"})

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
        # Override this function too.
        return '/'

    @property
    def envoy_host(self) -> str:
        return "flowd.rexflow.svc.cluster.local"