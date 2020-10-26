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
% python -m deploy
```

Tear-down REXFlow K8s resources
-------------------------------

```console
% python -m deploy delete
```
