#!/usr/bin/env python3

import setuptools
from rex.setuptools.setup import rex_setup_args

with open("README.md", "r", encoding="utf-8") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(**rex_setup_args(
    long_description=LONG_DESCRIPTION,
    description='A utility library for workflow orchestration',
    entry_points={'console_scripts': ['flowctl=flowctl.__main__:main']},
    install_requires=[
        'boto3',
        'confluent-kafka',
        'etcd3',
        'grpcio',
        'isodate',
        'pyyaml',
        'quart',
        'requests',
        'xmltodict',
    ],
    long_description_content_type='text/markdown',
    # TODO: call this "rex-flowlib"/"rex.flowlib" instead of waffling
    # between "rexflowlib" and "flowlib"
    name='rexflowlib',
    packages=[
        'flowctl',
        'flowctl.actions',
        'flowlib',
        'flowlib.configs',
        'rexflowlib',
    ],
    # TODO: There is currently no python-etcd3 conda package. Re-enable
    # this once there is one.
    rex_conda_name=None,
    python_requires='>=3.7',
    url='https://bitbucket.org/rexdev/rexflow',
))
