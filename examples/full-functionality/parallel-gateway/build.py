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
ENV FLASK_DEBUG 1
CMD [ "python", "./server.py"]
'''

DOCKER_TEMPLATE = '''FROM pgateway_base:latest
ENV SERVER_MODE {}
'''

SERVER_MODES = {'task0', 'task1', 'task2', 'task3'}

if __name__ == '__main__':
    if '--clean' in sys.argv:
        client = docker.from_env()
        image_set = set([tag for image in client.images.list() for tag in image.tags])
        tag_set = set([f'{repo}:latest' for repo in SERVER_MODES | {'pgateway_base'}])
        for tag in tag_set & image_set:
            client.images.remove(tag)
    mk_docker_cmd = lambda tag: ['docker', 'build', '-f', '-', '-t', tag, '.']
    subprocess.run(
        mk_docker_cmd('pgateway_base:latest'), input=BASE_DOCKERFILE, text=True)
    for mode in SERVER_MODES:
        subprocess.run(
            mk_docker_cmd(f'{mode}:latest'), input=DOCKER_TEMPLATE.format(mode),
            text=True)
