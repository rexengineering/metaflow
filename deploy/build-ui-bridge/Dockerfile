FROM python:3.8-slim AS base
WORKDIR /opt/rexflow
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt update && \
    apt install -y curl procps vim iputils-ping
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl
ENV ISTIO_VERSION=1.8.2
RUN curl -sL  https://istio.io/downloadIstioctl | sh - && \
    mv $HOME/.istioctl/bin/istioctl /usr/local/bin/istioctl

COPY flowlib flowlib/
COPY flowd flowd/
COPY uibridge uibridge/
COPY tools tools/

ENV PYTHONPATH=/opt/rexflow

FROM base AS test
CMD echo ignoring tests for now. i feel dirty.

FROM base AS container
EXPOSE 5000/tcp 5001/tcp
CMD [ "python", "-m", "uibridge", "-c", "flowlib.configs.development" ]
