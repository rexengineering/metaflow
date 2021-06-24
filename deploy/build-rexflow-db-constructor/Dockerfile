# syntax=docker/dockerfile:1

FROM python:3.8-slim AS base
WORKDIR /opt/rexflow
RUN apt-get update && apt-get install -y curl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY daemons/rexflow_db_manager.py .
FROM base AS test

FROM base AS container
CMD [ "python", "rexflow_db_manager.py"]