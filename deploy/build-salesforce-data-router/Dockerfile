# syntax=docker/dockerfile:1

FROM python:3.8-slim AS base
WORKDIR /opt/rexflow
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY daemons/salesforce-data-router.py .
FROM base AS test

FROM base AS container
CMD [ "python", "salesforce-data-router.py"]