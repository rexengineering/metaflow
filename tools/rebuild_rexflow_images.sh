#!/bin/bash

docker build -t flowd -f deploy/build-flowd/Dockerfile --target container .

docker build -t healthd -f deploy/build-healthd/Dockerfile  --target container .

docker build -t catch-gateway -f deploy/build-catch-gateway/Dockerfile --target container .

docker build -t throw-gateway -f deploy/build-throw-gateway/Dockerfile --target container .

docker build -t exclusive-gateway -f deploy/build-exclusive-gateway/Dockerfile --target container .

docker build -t parallel-gateway -f deploy/build-parallel-gateway/Dockerfile --target container .

docker build -t passthrough-container -f deploy/build-passthrough-container/Dockerfile --target container .

docker build -t async-bridge -f deploy/build-async-bridge/Dockerfile --target container .

docker build -t workflow-publisher -f deploy/build-workflow-publisher/Dockerfile --target container .

docker build -t rexflow-db-manager -f deploy/build-rexflow-db-constructor/Dockerfile --target container .

docker build -t salesforce-data-router -f deploy/build-salesforce-data-router/Dockerfile --target container .
