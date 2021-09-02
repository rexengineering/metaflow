import asyncio
import logging

import argparse
import importlib
from typing import Union
from grpc.experimental import aio

from flowlib import flow_pb2_grpc
from flowlib.flowd_utils import get_log_format

from .flow_daemon import Flow
from .flow_app import FlowApp


async def serve(host: str, port: Union[str, int]):
    address = f'{host}:{port}'
    server = aio.server()
    flow_pb2_grpc.add_FlowDaemonServicer_to_server(Flow(), server)
    server.add_insecure_port(address)
    logging.info(f'Starting flowd on port {address}...')
    await server.start()
    await server.wait_for_termination()
    logging.info('Terminated flowd.')


def build_parser():
    parser = argparse.ArgumentParser(
        prog='flowd', description='REX Flow daemon.'
    )
    parser.add_argument('--level', default='INFO', help='set logging level')
    parser.add_argument(
        '-c', '--config', nargs=1, help='configuration module name', type=str
    )
    return parser


def build_app():
    config = None
    namespace = build_parser().parse_args()
    if namespace.config:
        config = importlib.import_module(namespace.config[0]).__dict__
    logging.basicConfig(format=get_log_format('flowd'),
                        level=getattr(logging, namespace.level, logging.INFO))
    loop = asyncio.get_event_loop()
    loop.create_task(serve('[::]', 9001))
    return FlowApp(bind='0.0.0.0:9002', config=config)


if __name__ == '__main__':
    # The following must run in the main thread.
    build_app().run_serve()
