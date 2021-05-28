import io
import sys
import subprocess

import docker

BASE_DOCKERFILE = '''FROM python:3.8-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 5000/tcp
CMD [ "python", "./server.py"]
'''

DOCKER_TEMPLATE = '''FROM amort_base:latest
ENV SERVER_MODE {}
ENV SLEEP_TIME {}
'''

BASE_IMAGE = 'amort_base'

SERVER_MODES = {'amort-calc', 'amort-best-rate'}
SLEEP_TIME = 0

if __name__ == '__main__':
    if '--clean' in sys.argv:
        client = docker.from_env()
        image_set = set([tag for image in client.images.list() for tag in image.tags])
        tag_set = set([f'{repo}:latest' for repo in SERVER_MODES | {BASE_IMAGE}])
        for tag in tag_set & image_set:
            client.images.remove(tag)
    mk_docker_cmd = lambda tag: ['docker', 'build', '-f', '-', '-t', tag, '.']
    subprocess.run(
        mk_docker_cmd(f'{BASE_IMAGE}:latest'), input=BASE_DOCKERFILE, text=True)
    for mode in SERVER_MODES:
        subprocess.run(
            mk_docker_cmd(f'{mode}:latest'), input=DOCKER_TEMPLATE.format(mode,SLEEP_TIME),
            text=True)

