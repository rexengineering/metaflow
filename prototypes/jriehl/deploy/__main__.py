import argparse

import kubernetes.config

from . import deployer

kubernetes.config.load_kube_config()

parser = argparse.ArgumentParser('deploy')
parser.add_argument(
    'subcommand', nargs='?', default='create', choices=('create', 'delete')
)

if __name__ == '__main__':
    my_deployer = deployer.Deployer()
    namespace = parser.parse_args()
    if hasattr(my_deployer, namespace.subcommand):
        getattr(my_deployer, namespace.subcommand)(namespace)
    else:
        raise NotImplementedError(f'No handler for {namespace.subcommand} '
                                  'subcommand!')
