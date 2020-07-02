import argparse
import sys
import traceback

from .cli import build_parser_and_action_map

if __name__ == '__main__':
    parser, actions = build_parser_and_action_map()
    namespace = parser.parse_args()
    try:
        result = actions[namespace.command](namespace)
        sys.exit(result if result is not None else 0)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit(-1)
