FROM python:3.8-slim AS catch-base
WORKDIR /opt/rexflow
RUN apt-get update && apt-get install -y curl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY catchgateway.py .
EXPOSE 5050/tcp

FROM catch-base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM catch-base AS catch-container

CMD ["python", "-m", "catchgateway"]
