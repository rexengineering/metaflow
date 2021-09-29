FROM python:3.8-slim AS xgw-base
WORKDIR /opt/rexflow
RUN apt-get update && apt-get install -y curl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY bpmn_containers/exclusivegateway.py .
EXPOSE 5050/tcp

FROM xgw-base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM xgw-base AS container

CMD ["python", "-m", "exclusivegateway"]
