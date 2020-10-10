Rough deployment notes:

Build REXFlow containers:

```console
% docker build -f deploy/Dockerfile.flowd -t flowd .
% docker build -f deploy/Dockerfile.healthd -t healthd .
```

Start `etcd`, configuring it to listen at the host's IP address:

```console
% export HOST_IP=$(python -c \
    "import socket; print(socket.gethostbyname(socket.getfqdn()))")
% etcd --initial-advertise-peer-urls http://${HOST_IP}:2380 \
    --listen-peer-urls http://${HOST_IP}:2380 \
    --advertise-client-urls http://${HOST_IP}:2379 \
    --listen-client-urls http://${HOST_IP}:2379 \
    --initial-cluster node1=http://${HOST_IP}:2380
```

Deploy REXFlow K8s resources:

```console
% python -m deploy
```
