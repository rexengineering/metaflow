import io
import sys
import subprocess

import docker

DOCKERFILE = '''FROM python:3.8-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 5000/tcp
CMD [ "python", "./server.py"]
'''

SERVER_MODES = {'favorite-food'}

if __name__ == '__main__':
    subprocess.run(
        'docker build -f - -t favorite-food .'.split(),
        input=DOCKERFILE,
        text=True,
    )


