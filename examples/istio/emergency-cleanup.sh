#!/bin/bash
kubectl delete --ignore-not-found services collect secret-sauce profit xgateway-did-apply
kubectl delete --ignore-not-found deployments collect secret-sauce profit xgateway-did-apply
kubectl delete --ignore-not-found serviceaccounts collect secret-sauce profit xgateway-did-apply
kubectl delete --ignore-not-found virtualservices.networking.istio.io collect secret-sauce profit xgateway-did-apply
kubectl delete --ignore-not-found envoyfilters.networking.istio.io hijack-collect hijack-secret-sauce hijack-profit
