Example of using Istio management of Kubernetes orchestration.
==============================================================

This demo assumes a clean room setup.  That means that while you are using
Istio, you do not have automatic sidecar injection configured for the `default`
namespace (the Flow Daemon will setup the sidecar for you).  It also assumes you
have no other Istio gateways or virtual services running.  Running the REXFlow
system under different conditions is outside the scope of this example.

It also assumes you have built or pulled a copy of the `rex-proxy:1.8.2`
container using a blessed branch containing the BAVS filter with support for
REXFlow response routing.  For details on building this container, see the
README for the REX `istio-proxy` repository.

Lastly, you must set the `ISTIO_VERSION` environment variable to the version
of your istio: see `istioctl version`, and you must set `REX_ISTIO_PROXY_IMAGE`
to the image name for your preferred Istio Proxy image (the one described in
the above paragraph).

Preliminaries
-------------

First, ensure you are using the `docker-desktop` context for Kubernetes:

```console
% kubectl config use-context docker-desktop
```

Second, if you haven't already, be sure to setup your Python environment for use
of `flowctl`:

```console
% cd <...>/rexflow/prototypes/jriehl
% pip install -r requirements.txt
% export PYTHONPATH=$(pwd)
```

Third, build and stand up the Flow Daemon and its infrastructure:

```console
% docker build -f deploy/Dockerfile.flowd -t flowd .
% docker build -f deploy/Dockerfile.healthd -t healthd .
% python -m deploy create
```
*NOTE* If you make changes to any code that affects `flowd`, you must re-run the
build command above and then bounce the flowd pod.

Ensure the Flow Daemon comes up.  You should see something like follows:

```console
% kubectl get pods -n rexflow
NAME                           READY   STATUS    RESTARTS   AGE
flowd-55c5876466-fvwjp         1/1     Running   0          14s
healthd-7675dc5c99-7lhn5       1/1     Running   0          14s
rexflow-etcd-6c879bc4b-djhft   1/1     Running   0          14s
```

Fourth, configure your `flowctl` tool to use the Flow Daemon you just set up:

```console
% export FLOWD_HOST=localhost
% export FLOWD_PORT=80
% python -m flowctl ps
2020-10-26 11:06:02,252|flowctl|INFO|ps_action.py:40|Got response: 0, "Ok", {}
```

The last command illustrates the expected output of a successful connection from
`flowctl` to `flowd`.

Finally, ensure you've built the three service containers, `collect`,
`secret-sauce`, and `profit` in the `underpants` example:

```console
% pushd examples/underpants
% python build.py --clean
...
% popd
```

Running the Example
-------------------

Deploy the workflow:

```console
% python -m flowctl apply examples/istio/istio-underpants.bpmn
2020-10-26 13:26:49,388|flowctl|INFO|apply_action.py:62|Got response: 0, "Ok", {"Underpants": "Underpants-cf7d1e2817b811ebb421ea625718c50e"}
% WF_PROC=Underpants-cf7d1e2817b811ebb421ea625718c50e
```

Wait for the deployment to enter the `RUNNING` state, and then verify the
constituent pods are running:

```console
% watch python -m flowctl ps -k DEPLOYMENT
% kubectl get pods
NAME                           READY   STATUS    RESTARTS   AGE
collect-59b59756b5-s7pds       2/2     Running   0          6m22s
profit-7ffccc964c-jmsq4        2/2     Running   0          6m22s
secret-sauce-9d5c88fcc-lmv9b   2/2     Running   0          6m22s
```

Run a workflow instance:

```console
% python -m flowctl run $WF_PROC '{}'
2020-10-26 13:34:04,455|flowctl|INFO|run_action.py:38|Got response: 0, "Ok", {"Underpants-cf7d1e2817b811ebb421ea625718c50e": "flow-d334c20e17b911ebb421ea625718c50e"}
```

Wait for the instance to enter the `COMPLETED` state, and then observe the
results:

```console
% watch python -m flowctl ps
% python -m flowctl ps -o | jq .
2020-10-26 13:34:49,897|flowctl|INFO|ps_action.py:40|Got response: 0, "Ok", {"flow-d334c20e17b911ebb421ea625718c50e": {"result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Collected.\"}\n", "state": "COMPLETED"}}
{
  "flow-d334c20e17b911ebb421ea625718c50e": {
    "result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Collected.\"}\n",
    "state": "COMPLETED"
  }
}
```

Clean up the workflow instance records:

```console
% python -m flowctl delete flow-d334c20e17b911ebb421ea625718c50e
2020-10-26 13:35:26,315|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"flow-d334c20e17b911ebb421ea625718c50e": {"result": 0, "message": "Successfully deleted flow-d334c20e17b911ebb421ea625718c50e."}}
```

Stop the deployment, waiting for it to enter the `STOPPED` state:

```console
% python -m flowctl stop -k DEPLOYMENT $WF_PROC
2020-10-26 13:35:45,813|flowctl|INFO|stop_action.py:32|Got response: 0, "Ok", {"Underpants-cf7d1e2817b811ebb421ea625718c50e": {"status": 0, "message": "Stopped."}}
% watch python -m flowctl ps --k DEPLOYMENT
```

Delete the deployment data, verify it's no longer being tracked, and verify all
pod have been deleted:

```console
% python -m flowctl delete --k DEPLOYMENT $WF_PROC
2020-10-26 13:36:27,700|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"Underpants-cf7d1e2817b811ebb421ea625718c50e": {"result": 0, "message": "Successfully deleted Underpants-cf7d1e2817b811ebb421ea625718c50e."}}
% python -m flowctl ps -k DEPLOYMENT
2020-10-26 13:36:43,399|flowctl|INFO|ps_action.py:40|Got response: 0, "Ok", {}
% kubectl get pods
No resources found in default namespace.
```

### Summary/TL;DR

```console
python -m flowctl apply examples/istio/istio-underpants.bpmn
watch python -m flowctl ps -k DEPLOYMENT
WF_PROC=Underpants-...
python -m flowctl run $WF_PROC {}
watch python -m flowctl ps
python -m flowctl ps
python -m flowctl delete flow-...
python -m flowctl stop -k DEPLOYMENT $WF_PROC
watch python -m flowctl ps --k DEPLOYMENT
python -m flowctl delete --k DEPLOYMENT $WF_PROC
```

Cleaning Up
-----------

To clean up the Flow Daemon you've deployed, use the following:

```console
% python -m deploy delete
% kubectl get pods -n rexflow
NAME                       READY   STATUS        RESTARTS   AGE
flowd-55c5876466-fvwjp     0/1     Terminating   0          165m
healthd-7675dc5c99-7lhn5   0/1     Terminating   0          165m
```
The second line uses `kubectl` to verify that the Flow Daemon is being
terminated by the automation.
