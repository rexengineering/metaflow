FROM python:3.8-slim AS throw-base
WORKDIR /opt/rexflow
RUN apt-get update && apt-get install -y curl
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY flowlib flowlib/
COPY throwgateway.py .
EXPOSE 5050/tcp

FROM throw-base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM throw-base AS container

CMD ["python", "-m", "throwgateway"]
