#!/bin/bash

kubectl config use-context docker-desktop
cd ../.. && docker build -t flowd -f deploy/Dockerfile.flowd . && docker build -t healthd -f deploy/Dockerfile.healthd .
kubectl config set-context --current --namespace=default

function findall()
  {
  kubectl get $1 | grep -E '(catch|throw|collect|sauce|did-apply|profit)' | cut -d ' ' -f1
  }
function cleanup()
  {
  for s in $(findall $1) ; do  kubectl delete $1 $s ; done
  }
cleanup svc
cleanup deployment
cleanup serviceaccount
cleanup envoyfilter
cleanup virtualservice


kubectl delete envoyfilter -nmy-ns --all

kubectl delete ns --ignore-not-found conditional events no-sauce gnomes-v1 throw

kubectl delete po --all -nrexflow


