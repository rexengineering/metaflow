import argparse
import logging

parser = argparse.ArgumentParser(prog='flowc')
parser.add_argument(
    'sources', metavar='source', nargs='*', type=open,
    help='input source file(s)'
)
parser.add_argument(
    '--log_level', nargs=1, default=logging.INFO, type=int,
    help=f'logging level (DEBUG={logging.DEBUG}, INFO={logging.INFO}...)'
)
parser.add_argument(
    '-o', '--output_path', nargs=1, default='.', type=str,
    help='target output path (defaults to .)'
)
