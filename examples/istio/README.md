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

In order to download the istio proxy you can run the following command
``` 
% docker pull 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/istio-proxy:1.8.2-branch.rex.sh
% docker tag 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/istio-proxy:1.8.2-branch.rex.sh rex-proxy:1.8.2
```

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

Second, Install Istio on our cluster
```
% istioctl install --set profile=demo
```
Third, if you haven't already, be sure to setup your Python environment for use
of `flowctl`:

```console
% cd rexflow/
% pip install -r requirements.txt
% export PYTHONPATH=$(pwd)
```

Fourth, build and stand up the Flow Daemon and its infrastructure:

```console
% ./tools/rebuild_rexflow_images.sh
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
Fifth, build and deploy the dmnserver container.

This requires you to checkout the rexflow-dmn-server repo, and in that repo:

```
% ./build.sh && ./deploy.sh

```
Check to see that the container is running in the rexflow namespace:

```
NAME                            READY   STATUS    RESTARTS   AGE
dmnserver-6d566d7695-lwz5r      1/1     Running   0          14s
flowd-55c5876466-fvwjp          1/1     Running   0          24m
healthd-7675dc5c99-7lhn5        1/1     Running   0          24m
rexflow-etcd-6c879bc4b-djhft    1/1     Running   0          24m

```

Sixth, configure your `flowctl` tool to use the Flow Daemon you just set up:

```console
-- return to your rexflow repo
% export FLOWD_HOST=localhost
% export FLOWD_PORT=80
% python -m flowctl ps
2021-06-09 15:34:02,914|flowctl|INFO|ps_action.py:95|Got response: 0, "Ok", {"underpants-ea006594-c137596ac94b11eba03f3ec61292c177": {"content_type": "application/json", "end_event": "end-underpants", "parent": "underpants-ea006594", "result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Not collected ):\"}\n", "state": "COMPLETED"}}
```

The last command illustrates the expected output of a successful connection from
`flowctl` to `flowd`.

Finally, ensure you've built the three service containers, `collect`,
`secret-sauce`, and `profit` in the `underpants` example:

```console
% pushd examples/underpants
% python build.py
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
% kubectl get pods
NAME                           READY   STATUS    RESTARTS   AGE
collect-59b59756b5-s7pds       2/2     Running   0          6m22s
profit-7ffccc964c-jmsq4        2/2     Running   0          6m22s
secret-sauce-9d5c88fcc-lmv9b   2/2     Running   0          6m22s
```

Run a workflow instance:

```console
% python -m flowctl run $WF_PROC '{}'
2021-06-09 15:45:46,505|flowctl|INFO|run_action.py:55|Got response: 0, "Ok", {"id": "underpants-ea006594-6e1243a2c97411eba03f3ec61292c177", "message": "Ok", "status": 0}
```

Wait for the instance to enter the `COMPLETED` state, and then observe the
results:

```console
% watch python -m flowctl ps
% python -m flowctl ps -o | jq .
2021-06-09 15:47:54,829|flowctl|INFO|ps_action.py:95|Got response: 0, "Ok", {"underpants-ea006594-6e1243a2c97411eba03f3ec61292c177": {"content_type": "application/json", "end_event": "end-underpants", "parent": "underpants-ea006594", "result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Not collected ):\"}\n", "state": "COMPLETED"}}
{
  "underpants-ea006594-6e1243a2c97411eba03f3ec61292c177": {
    "content_type": "application/json",
    "end_event": "end-underpants",
    "parent": "underpants-ea006594",
    "result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Not collected ):\"}\n",
    "state": "COMPLETED"
  }
}
```

Clean up the workflow instance records:

```console
% python -m flowctl delete -i underpants-ea006594-6e1243a2c97411eba03f3ec61292c177
2021-06-09 15:49:08,400|flowctl|INFO|delete_action.py:60|Got response: 0, "Ok", {"underpants-ea006594-6e1243a2c97411eba03f3ec61292c177": {"result": 0, "message": "Successfully deleted underpants-ea006594-6e1243a2c97411eba03f3ec61292c177."}}
```

Stop the deployment, waiting for it to enter the `STOPPED` state:

```console
% python -m flowctl stop -k DEPLOYMENT $WF_PROC
2021-06-09 15:50:42,502|flowctl|INFO|stop_action.py:51|Got response: 0, "Ok", {"underpants-ea006594": {"status": 0, "message": "Stopped."}}
% watch python -m flowctl ps --k DEPLOYMENT
```

Delete the deployment data, verify it's no longer being tracked, and verify all
pod have been deleted:

```console
% python -m flowctl delete -k DEPLOYMENT $WF_PROC
2021-06-09 15:52:05,460|flowctl|INFO|delete_action.py:60|Got response: 0, "Ok", {"underpants-ea006594": {"result": 0, "message": "Successfully deleted underpants-ea006594."}}
% python -m flowctl ps -k DEPLOYMENT
2021-06-09 15:52:39,870|flowctl|INFO|ps_action.py:95|Got response: 0, "Ok", {}
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
