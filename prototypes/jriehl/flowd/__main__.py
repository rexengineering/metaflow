from concurrent import futures
import logging
import multiprocessing as mp

import argparse
import grpc

from flowlib import flow_pb2, flow_pb2_grpc, executor
from flowlib.flowd_utils import get_log_format

from .flow_daemon import Flow
from .flow_app import app


def serve(the_executor, host, port):
    server = grpc.server(the_executor)
    flow_pb2_grpc.add_FlowDaemonServicer_to_server(Flow(), server)
    server.add_insecure_port(f'{host}:{port}')
    logging.info(f'Starting flowd on port {port}...')
    server.start()
    server.wait_for_termination()
    logging.info('Terminated flowd.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='flowd', description='REX Flow daemon.')
    parser.add_argument('--level', default='INFO', help='set logging level')
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('flowd'),
                        level=getattr(logging, namespace.level, logging.INFO))
    the_executor = executor.get_executor()
    grpc_future = the_executor.submit(serve, the_executor, '[::]', 9001)
    app_future = the_executor.submit(app.run, host='0.0.0.0', port=9002)
    futures.wait([grpc_future, app_future])
