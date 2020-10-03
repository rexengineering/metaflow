Rough deployment notes:

Build REXFlow containers:

```console
% docker build -f deploy/Dockerfile.flowd -t flowd .
% docker build -f deploy/Dockerfile.healthd -t healthd .
```

Start `etcd`, configuring it to listen at the host's IP address:

```console
% etcd --initial-advertise-peer-urls http://${HOST}:2380 \
    --listen-peer-urls http://${HOST}:2380 \
    --advertise-client-urls http://${HOST}:2379 \
    --listen-client-urls http://${HOST}:2379 \
    --initial-cluster node1=http://${HOST}:2380
```

Deploy REXFlow K8s resources:

```console
% python -m deploy
```
