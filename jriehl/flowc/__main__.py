import logging
import sys

from flowlib.flowd_utils import get_log_format
from .parser import parser
from .flowclib import flow_compiler

if __name__ == '__main__':
    namespace = parser.parse_args()
    logging.basicConfig(
        format=get_log_format('flowc'), level=namespace.log_level
    )
    if len(namespace.sources) == 0:
        if not flow_compiler(sys.stdin, namespace.output_path):
            sys.exit(1)
    else:
        if not all(
            flow_compiler(source, namespace.output_path)
            for source in namespace.sources
        ):
            sys.exit(1)
