Cluster deployment notes
========================

Build REXFlow containers
------------------------

Run from root of repository.
```console
% ./tools/rebuild_rexflow_images.sh
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
