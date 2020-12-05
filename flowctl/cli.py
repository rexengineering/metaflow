import argparse
import logging
import os

from .actions import (  # noqa
    apply_action,  # noqa
    delete_action,  # noqa
    ps_action,  # noqa
    run_action,  # noqa
    start_action,  # noqa
    stop_action,  # noqa
    restart_action,  # noqa
)  # noqa

ACTIONS = ('apply', 'delete', 'ps', 'restart', 'run', 'start', 'stop')


def add_action(action_name, subparsers, action_map):
    python_name = f'{action_name}_action'
    module = globals()[python_name]
    action_map[action_name] = getattr(module, python_name)
    subparser = subparsers.add_parser(
        action_name, help=module.__help__
    )
    subparser.add_argument(
        'command', action='store_const', const=action_name,
        help=argparse.SUPPRESS
    )
    module.__refine_args__(subparser)


def build_parser_and_action_map():
    parser = argparse.ArgumentParser(prog='flowctl')
    flowd_host = os.environ.get('FLOWD_HOST', 'localhost')
    parser.add_argument(
        '--flowd_host', nargs='?', default=flowd_host, type=str,
        help='hostname for the flowd server'
    )
    flowd_port = os.environ.get('FLOWD_PORT', 9001)
    parser.add_argument(
        '--flowd_port', nargs='?', default=flowd_port, type=int,
        help='port number for the flowd server'
    )
    parser.add_argument(
        '--log_level', nargs='?', default=logging.INFO, type=int,
        help=f'logging level (DEBUG={logging.DEBUG}, INFO={logging.INFO}...)'
    )
    subparsers = parser.add_subparsers(title='command')
    action_map = dict()
    for action in ACTIONS:
        add_action(action, subparsers, action_map)
    return parser, action_map
