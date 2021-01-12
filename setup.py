import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rexflow", # Replace with your own username
    version="0.0.1",
    author="REXFlow Developers",
    author_email="engineering@rexchange.com",
    description="A framework for workflow orchestration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://bitbucket.org/rexdev/rexflow",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.8',
)
