FROM python:3.8-slim AS base
WORKDIR /opt/rexflow
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt update && \
    apt install -y curl
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl
ENV ISTIO_VERSION=1.8.2
RUN curl -sL  https://istio.io/downloadIstioctl | sh - && \
    mv $HOME/.istioctl/bin/istioctl /usr/local/bin/istioctl

COPY flowlib flowlib/
COPY daemons/healthd.py .
EXPOSE 5050/tcp

FROM base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM base AS container

CMD ["python", "-m", "healthd"]
