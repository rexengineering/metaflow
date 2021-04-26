#!/bin/bash

set -ex
rex-k8s-context $1

for image in {flowd,healthd,throw-gateway,catch-gateway,exclusive-gateway,parallel-gateway} ; do
  rex-ecr-tag --repo rex/rexflow-$image --image b-master --move --tag $1;
done

rex-k8s-context $1:rexflow

kubectl rollout restart deployment flowd
kubectl rollout restart deployment healthd
