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
    log_level = int(getattr(logging, namespace.level, logging.INFO))
    print(f'log_level is {log_level}', flush=True)
    log_format = get_log_format('ui-bridge')
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_handler = root_logger.handlers[0]
    root_handler.setLevel(log_level)
    root_handler.setFormatter(logging.Formatter(log_format))
    app = REXFlowUIBridge(bind=f'0.0.0.0:{UI_BRIDGE_PORT}', config=config)
    app.run_serve()
