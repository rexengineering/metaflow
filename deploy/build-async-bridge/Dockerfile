FROM python:3.8-slim AS base
WORKDIR /opt/rexflow
RUN apt-get update && apt-get install -y curl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY bpmn_containers/async_service_bridge.py .
EXPOSE 5050/tcp

FROM base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM base AS container

CMD ["python", "-m", "async_service_bridge"]
