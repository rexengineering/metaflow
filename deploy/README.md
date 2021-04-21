Cluster deployment notes
========================

Build REXFlow containers
------------------------

Run from root of repository.
```console
% docker build -f deploy/Dockerfile.flowd --target container -t flowd .
% docker build -f deploy/Dockerfile.healthd --target container -t healthd .
% docker build -f deploy/Dockerfile.catch --target container -t catch-gateway .
% docker build -f deploy/Dockerfile.throw --target container -t throw-gateway .
% pushd gateway_containers/exclusive-gateway && docker build -f Dockerfile --target container -t exclusive-gateway . && popd
% pushd gateway_containers/parallel-gateway && docker build -f Dockerfile --target container -t parallel-gateway . && popd
```

Deploy REXFlow K8s resources
----------------------------

```console
% python -m deploy --kafka  # --kafka flag is optional.
```

Tear-down REXFlow K8s resources
-------------------------------

```console
% python -m deploy delete --kafka  # only use --kafka flag if deployed with kafka
```
