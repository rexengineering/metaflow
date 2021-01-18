#!/bin/bash

unset HISTFILE

pushd $(dirname $(readlink -f $0))

function findall()
  {
  objtype=$1
  shift
  kubectl get $objtype "$@" | grep -E '(start-|end-|under|default-up|catch|throw|test|collect|sauce|did-apply|profit|pgateway-test-one|pgateway-did-apply|pgateway-splitter1|pgateway-combiner1|task0|task1|task2|task3|start-ptest|end-finish)' | cut -d ' ' -f1
  }

function cleanup-namespace()
  {
  objtype=$1
  shift
  for s in $(findall $objtype "$@") ; do kubectl delete $objtype $s "$@"; done
  }

function cleanup()
  {
  cleanup-namespace $1 -n default
  cleanup-namespace $1 -n conditional
  cleanup-namespace $1 -n ptest
  kubectl delete namespace conditional --ignore-not-found
  kubectl delete namespace ptest --ignore-not-found
  }

cleanup svc
cleanup deployment
cleanup serviceaccount
cleanup envoyfilter
cleanup virtualservice

kubectl delete po --all -nrexflow

popd
