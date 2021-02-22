FROM python:3.8-slim AS base
LABEL maintainer="REX Engineering <engineering@rexchange.com>"
COPY . /opt/rexflow
WORKDIR /opt/rexflow
RUN pip install -r requirements.txt

FROM base AS build
RUN python setup.py bdist_wheel
RUN pip install dist/*.whl

FROM build AS test
ENV PYTHONPATH=.
RUN python -m tests

FROM build AS container
WORKDIR /
EXPOSE 9001/tcp 9002/tcp
RUN apt update && \
    apt install -y curl
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl
ENV ISTIO_VERSION=1.8.2
RUN curl -sL  https://istio.io/downloadIstioctl | sh - && \
    mv $HOME/.istioctl/bin/istioctl /usr/local/bin/istioctl
CMD [ "python", "-m", "flowd" ]
