#!/usr/bin/env python
'''Utility to get a map from BPMN file paths to the REXFlow hash corresponding to
that BPMN file.  Useful for predetermining the name of a workflow deployment.
'''

from collections import OrderedDict
import xmltodict

from flowlib.bpmn import BPMNProcess


def main(*args):
    result = {}
    for path in args:
        with open(path, 'rb') as file_obj:
            xmldict = xmltodict.parse(file_obj)
            assert xmldict is not None
            assert 'bpmn:definitions' in xmldict
            assert 'bpmn:process' in xmldict['bpmn:definitions']
            process = BPMNProcess(xmldict['bpmn:definitions']['bpmn:process'])
            result[path] = process.hash
    return result


if __name__ == '__main__':
    import sys, pprint
    result = main(*sys.argv[1:])
    pprint.pprint(result)
