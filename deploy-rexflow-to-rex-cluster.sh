#!/bin/bash

set -ex
rex-k8s-context $1

FLOWD_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-flowd:$1
docker build -t $FLOWD_TAG -f deploy/Dockerfile.flowd .
docker push $FLOWD_TAG

HEALTHD_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-healthd:$1
docker build -t $HEALTHD_TAG -f deploy/Dockerfile.healthd .
docker push $HEALTHD_TAG

CATCH_IMAGE_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-catch-gateway:$1
docker build -t $CATCH_IMAGE_TAG -f deploy/Dockerfile.catch .
docker push $CATCH_IMAGE_TAG

THROW_IMAGE_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-throw-gateway:$1
docker build -t $THROW_IMAGE_TAG -f deploy/Dockerfile.throw .
docker push $THROW_IMAGE_TAG

# TODO: Pull the exclusive-gateway and parallel-gateway out of the `gateway_containers` directory
REXFLOW_ROOT=$PWD
cd $REXFLOW_ROOT/gateway_containers/exclusive-gateway && make build
XGW_IMAGE_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-exclusive-gateway:$1
docker tag exclusive-gateway:1.0.0 $XGW_IMAGE_TAG  # the 1.0.0 comes from `make build` 2 lines up.
docker push $XGW_IMAGE_TAG

cd $REXFLOW_ROOT/gateway_containers/parallel-gateway && make build
PGW_IMAGE_TAG=355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-parallel-gateway:$1
docker tag parallel-gateway:1.0.0 $PGW_IMAGE_TAG  # the 1.0.0 comes from `make build` 2 lines up.
docker push $PGW_IMAGE_TAG

rex-k8s-context $1:rexflow

kubectl rollout restart deployment flowd
kubectl rollout restart deployment healthd
