import argparse
import logging

import kubernetes.config

from . import deployer
from flowlib.flowd_utils import get_log_format

kubernetes.config.load_kube_config()

parser = argparse.ArgumentParser('deploy')
parser.add_argument(
    'subcommand', nargs='?', default='create', choices=('create', 'delete')
)
parser.add_argument(
    '--kafka', action='store_true'
)

if __name__ == '__main__':
    my_deployer = deployer.Deployer()
    namespace = parser.parse_args()
    logging.basicConfig(format=get_log_format('deploy'))
    if hasattr(my_deployer, namespace.subcommand):
        getattr(my_deployer, namespace.subcommand)(namespace)
    else:
        raise NotImplementedError(f'No handler for {namespace.subcommand} '
                                  'subcommand!')
