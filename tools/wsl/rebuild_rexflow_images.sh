#!/bin/bash

docker build -t flowd -f deploy/build-flowd/Dockerfile --target container .

docker build -t healthd -f deploy/build-healthd/Dockerfile  --target container .

docker build -t catch-gateway -f tools/wsl/Dockerfile.catch --target catch-container .

docker build -t throw-gateway -f tools/wsl/Dockerfile.throw --target throw-container .

docker build -t exclusive-gateway -f tools/wsl/Dockerfile.exclusive --target exclusive-container .

docker build -t parallel-gateway -f tools/wsl/Dockerfile.parallel --target parallel-container .

docker build -t passthrough-container -f tools/wsl/Dockerfile.passthrough --target passthrough-container .

docker build -t ui-bridge -f uibridge/Dockerfile.uibridge .