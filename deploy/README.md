Cluster deployment notes
========================

Build REXFlow containers
------------------------

```console
% docker build -f deploy/Dockerfile.flowd -t flowd .
% docker build -f deploy/Dockerfile.healthd -t healthd .
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
