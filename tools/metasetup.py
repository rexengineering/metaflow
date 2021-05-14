'''Utility to generate setup.py for REXFlow.

Usage:
    % python -m tools.metasetup > setup.py
'''
import os.path
from subprocess import check_output
import sys

import jinja2

GIT_VERSION = check_output('git describe --abbrev=4 --dirty --always'.split()).decode('utf-8').strip()

TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_PATH),
    autoescape=jinja2.select_autoescape(['.py']),
)

SETUP_TEMPLATE = JINJA_ENVIRONMENT.get_template('setup.py.jinja2')


def main(*args):
    if len(args) == 0:
        args = (sys.stdout,)
    setup_py_str = SETUP_TEMPLATE.render(git_version=GIT_VERSION)
    for arg in args:
        if isinstance(arg, str):
            with open(arg, 'w') as file_obj:
                print(setup_py_str, file=file_obj, flush=True)
        else:
            print(setup_py_str, file=arg, flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
