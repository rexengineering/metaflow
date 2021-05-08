import setuptools
from subprocess import check_output

git_version = check_output("git describe --abbrev=4 --dirty --always".split()).decode('utf-8').strip()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flowlib",  # NOTE: Hopefully this is temporary; see REXFLOW-190.
    version=git_version,
    author="REXFlow Developers",
    author_email="engineering@rexchange.com",
    description="A utility library for workflow orchestration",
    long_description=long_description,  # TODO: Make this flowlib specific...
    long_description_content_type="text/markdown",
    url="https://bitbucket.org/rexdev/rexflow",
    packages=['flowlib', 'flowlib.configs'],
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=[
        'boto3',
        'confluent-kafka',
        'etcd3',
        'grpcio',
        'quart',
        'xmltodict',
    ],
    python_requires='>=3.8',
)
