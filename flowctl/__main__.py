import logging
import sys
import traceback

from flowlib.flowd_utils import get_log_format

from .cli import build_parser_and_action_map

if __name__ == '__main__':
    parser, actions = build_parser_and_action_map()
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('flowctl'), level=namespace.log_level)
    if not hasattr(namespace, 'command'):
        parser.print_help()
        sys.exit(1)
    try:
        result = actions[namespace.command](namespace)
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error(f'Unexpected top level exception: {exc_value}')
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit(-1)
    sys.exit(result if type(result) is int else 0)
