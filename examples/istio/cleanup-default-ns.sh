#!/bin/bash

kubectl config use-context docker-desktop

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


