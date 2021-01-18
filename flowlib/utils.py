
# utils.py
#
#   General purpose utility functions, constants, and more.  Stand-alone util funcs and small
# groups of related util funcs can be placed here, and promoted / migrated to their own files if
# and when they outgrow this catch-all utility package.


import logging
import pprint

from sys import stderr

from .etcd_utils import EtcdDict, get_dict_from_prefix


elog = logging.error
wlog = logging.warn
ilog = logging.info
dlog = logging.debug

log = ilog


@contextmanager
def get_flowd_connection(host : str, port : int, *_, **kws):
    opts = [('grpc.default_authority', 'flowd:9001')]
    opts.extend(list(kws.items()))
    with grpc.insecure_channel(f'{host}:{port}', opts) as channel:
        server_proxy = flow_pb2_grpc.FlowDaemonStub(channel)
        yield server_proxy


def get_log_format(prog, verbose=False):
    if verbose:
        fileloc = '%(pathname)s'
    else:
        fileloc = '%(filename)s'
    return f'%(asctime)s|{prog}|%(levelname)s|{fileloc}:%(lineno)d|%(message)s'


def dprint(*params):
    '''
    Debug print: Always logs independent of logging config.
    '''
    print(*params, file=stderr)


def dpprint(*params):
    '''
    Debug pretty print: readably print any object to the logs.
    '''
    dprint(pprint.pformat(*params))


def detcddir(prefix):
    '''
    Debug etcd directory listing: readably print all etcd keys & values starting with prefix.
    '''
    dprint(f"prefix {prefix}:")
    dpprint(EtcdDict.from_root(prefix))

