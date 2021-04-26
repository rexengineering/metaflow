#!/bin/bash

docker build -t flowd -f deploy/build-flowd/Dockerfile --target container .

docker build -t healthd -f deploy/build-healthd/Dockerfile  --target container .

docker build -t catch-gateway -f deploy/build-catch-gateway/Dockerfile --target container .

docker build -t throw-gateway -f deploy/build-throw-gateway/Dockerfile --target container .

# build the exclusive-gateway. TODO: refactor exclusive gateway to be more like
# the others.
pushd gateway_containers/exclusive-gateway
docker build -t exclusive-gateway --target container -f Dockerfile .
popd

pushd gateway_containers/parallel-gateway
docker build -t parallel-gateway --target container -f Dockerfile .
popd





