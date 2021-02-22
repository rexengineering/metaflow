#!/bin/bash

kubectl config use-context docker-desktop

istioctl kube-inject -f $1 > /tmp/injected.yaml
sed 's/: Always/: IfNotPresent/g' /tmp/injected.yaml  > /tmp/injected1.yaml
sed 's/docker.io\/istio\/proxyv2:${ISTIO_VERSION}/${REX_ISTIO_PROXY_IMAGE}/g' /tmp/injected1.yaml  > /tmp/injected.yaml

kubectl apply -f /tmp/injected.yaml

