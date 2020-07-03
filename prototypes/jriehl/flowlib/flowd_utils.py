from contextlib import contextmanager

import grpc

from . import flow_pb2, flow_pb2_grpc

# Utility functions

@contextmanager
def get_flowd_connection(host : str, port : int, *args, **kws):
    with grpc.insecure_channel(f'{host}:{port}') as channel:
        server_proxy = flow_pb2_grpc.FlowDaemonStub(channel)
        yield server_proxy


def get_log_format(prog, verbose=False):
    if verbose:
        fileloc = '%(pathname)s'
    else:
        fileloc = '%(filename)s'
    return f'%(asctime)s|{prog}|%(levelname)s|{fileloc}:%(lineno)d|%(message)s'
