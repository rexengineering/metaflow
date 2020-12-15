# Integration Testing

This directory contains subdirectories with integration tests that demonstrate
and verify (almost) all of the behavior of the REXFlow system. These integration
tests are end-to-end, in that they run the `flowctl` commandline utility against
the `flowd` installation on your docker-desktop cluster. All testing is verified
through the `flowctl` utility.

### Assumptions

These integration test files will eventually be run on a Test Kitchen VM, which
is a self-contained environment capable of mimicking a Kubernetes Cluster. We
will work with Tyler's team to come up with a VM Image that contains a proper
k8s deployment with Kafka and Etcd already installed.

However, until that dream is a reality, we must assume the following:

* Your `docker-desktop` context has a fresh installation of REXFlow, via `python -m deploy create`.
* You have built the Underpants containers, via `cd examples/underpants && python -m build`.

For more information on how to set up your test environment, please see `examples/istio/README.md`