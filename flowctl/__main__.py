import logging
import sys
import traceback

from flowlib.flowd_utils import get_log_format

from .cli import build_parser_and_action_map


def main():
    parser, actions = build_parser_and_action_map()
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('flowctl'), level=namespace.log_level)
    if not hasattr(namespace, 'command'):
        parser.print_help()
        return 1
    try:
        result = actions[namespace.command](namespace)
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error(f'Unexpected top level exception: {exc_value}')
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        return -1
    return result if isinstance(result, int) else 0


if __name__ == '__main__':
    sys.exit(main())
