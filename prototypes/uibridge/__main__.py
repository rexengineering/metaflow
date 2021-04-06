import logging

import argparse
import importlib

from flowlib.config import UI_BRIDGE_PORT
from flowlib.flowd_utils import get_log_format

from .app import REXFlowUIBridge


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='uibridge', description='REX Flow UI Bridge.')
    parser.add_argument('--level', default='INFO', help='set logging level')
    parser.add_argument(
        '-c', '--config', nargs=1, help='configuration module name', type=str
    )
    namespace = parser.parse_args()
    config = None
    if namespace.config:
        config = importlib.import_module(namespace.config[0]).__dict__
    logging.basicConfig(format=get_log_format('uibridge'),
                        level=getattr(logging, namespace.level, logging.INFO))
    app = REXFlowUIBridge(bind=f'0.0.0.0:{UI_BRIDGE_PORT}', config=config)
    app.run()
