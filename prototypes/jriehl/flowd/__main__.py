from concurrent import futures
import logging
import multiprocessing as mp

import grpc

from flowlib import flow_pb2, flow_pb2_grpc
from flowlib.flowd_utils import get_log_format

from .flow_daemon import Flow


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=mp.cpu_count() * 2))
    flow_pb2_grpc.add_FlowDaemonServicer_to_server(Flow(), server)
    server.add_insecure_port('[::]:9001')
    logging.info('Starting flowd on port 9001...')
    server.start()
    server.wait_for_termination()
    logging.info('Terminated flowd.')


if __name__ == '__main__':
    logging.basicConfig(format=get_log_format('flowd'), level=logging.INFO)
    serve()
