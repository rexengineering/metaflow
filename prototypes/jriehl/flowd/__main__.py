import asyncio
import logging

import argparse
from typing import Union
from grpc.experimental import aio

from flowlib import flow_pb2_grpc, executor
from flowlib.flowd_utils import get_log_format

from .flow_daemon import Flow
from .flow_app import FlowApp


async def serve(host:str, port:Union[str,int]):
    address = f'{host}:{port}'
    server = aio.server()
    flow_pb2_grpc.add_FlowDaemonServicer_to_server(Flow(), server)
    server.add_insecure_port(address)
    logging.info(f'Starting flowd on port {address}...')
    await server.start()
    await server.wait_for_termination()
    logging.info('Terminated flowd.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='flowd', description='REX Flow daemon.')
    parser.add_argument('--level', default='INFO', help='set logging level')
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('flowd'),
                        level=getattr(logging, namespace.level, logging.INFO))
    loop = asyncio.get_event_loop()
    loop.create_task(serve('[::]', 9001))
    # The following must run in the main thread.
    app = FlowApp(bind='0.0.0.0:9002')
    app.run()
