#!/usr/bin/env python3
import xmltodict
from flowlib import bpmn
with open('time-test.bpmn', 'rb') as fp:
    spec = xmltodict.parse(fp)
process = bpmn.BPMNProcess(spec['bpmn:definitions']['bpmn:process'])
process.to_istio()
