import argparse
import logging

from .actions import apply_action, delete_action, ps_action, run_action, \
    start_action, stop_action

ACTIONS = ('apply', 'delete', 'ps', 'run', 'start', 'stop')


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
    parser.add_argument(
        '--flowd_host', nargs='?', default='localhost', type=str,
        help='hostname for the flowd server'
    )
    parser.add_argument(
        '--flowd_port', nargs='?', default=9001, type=int,
        help='port number for the flowd server'
    )
    parser.add_argument(
        '--log_level', nargs='?', default=logging.INFO, type=int,
        help=f'logging level (DEBUG={logging.DEBUG}, INFO={logging.INFO}...)'
    )
    subparsers =  parser.add_subparsers(title='command')
    action_map = dict()
    for action in ACTIONS:
        add_action(action, subparsers, action_map)
    return parser, action_map
