'''Utility to generate setup.py for REXFlow.

Usage:
    % python -m tools.metasetup [targets...]
'''
import os.path
import pprint
import shutil
from subprocess import check_output
import sys
from typing import Any, Dict

import jinja2


GIT_VERSION = check_output('git describe --abbrev=4 --dirty --always'.split()).decode('utf-8').strip()

TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

STAGE_PATH = os.path.join(TEMPLATE_PATH, 'stage')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_PATH),
    autoescape=jinja2.select_autoescape(['.py']),
)

SETUP_TEMPLATE = JINJA_ENVIRONMENT.get_template('setup.py.jinja2')

COMMON_SETTINGS = dict(
    author="REXFlow Developers",
    author_email="engineering@rexchange.com",
    description="A utility library for workflow orchestration",
    long_description_content_type="text/markdown",
    url="https://bitbucket.org/rexdev/rexflow",
    python_requires='>=3.7',
)

FLOWLIB_SETTINGS : Dict[str, Any] = COMMON_SETTINGS.copy()
FLOWLIB_SETTINGS.update(
    name='rexflowlib',
    packages=['flowlib', 'flowlib.configs'],
    install_requires=[
        'boto3',
        'confluent-kafka',
        'etcd3',
        'grpcio',
        'isodate',
        'PyYAML',
        'quart',
        'setuptools',
        'xmltodict',
    ],
)

FLOWCTL_SETTINGS : Dict[str, Any] = COMMON_SETTINGS.copy()
FLOWCTL_SETTINGS.update(
    name='rexflowctl',
    packages=['flowctl', 'flowctl.actions'],
    install_requires=[
        f'rexflowlib=={GIT_VERSION.split("-", 1)[0]}',
    ],
    entry_points= {
        'console_scripts': ['flowctl=flowctl.__main__:main']
    },
)

TARGETS = {}
for settings in (FLOWCTL_SETTINGS, FLOWLIB_SETTINGS):
    TARGETS[settings['name']] = settings


def main(*args):
    if len(args) == 0:
        args = tuple(TARGETS.keys())
    for target in args:
        settings = TARGETS[target]
        setup_py_str = SETUP_TEMPLATE.render(
            git_version=GIT_VERSION,
            setup_args=pprint.pformat(settings)
        )
        target_path = os.path.join(STAGE_PATH, target)
        target_file = os.path.join(target_path, 'setup.py')
        with open(target_file, 'w') as file_obj:
            print(setup_py_str, file=file_obj, flush=True)
        # NOTE: Watch the following assumption!  Getting fast and loose with
        # the packages setting will break this!
        code_path = settings['packages'][0]
        source_code = os.path.join(TEMPLATE_PATH, code_path)
        target_code = os.path.join(target_path, code_path)
        shutil.copytree(
            source_code,
            target_code,
            ignore=shutil.ignore_patterns('*.pyc', '__pycache__'),
            dirs_exist_ok=True,
        )


if __name__ == '__main__':
    main(*sys.argv[1:])
