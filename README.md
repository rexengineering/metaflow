REXFlow
=======

Architecture
============

This project contains four components:

* `flowlib` - This is a common library for both `flowctl` and `flowd`.  Contains
  important stuff including *protobuf* declarations, and client-server support
  code.
* `flowctl` - This is the primary command line interface to the proposed system.
* `flowd` - This is a prototype backend for the proposed system.
* `healthd` - This is a prototype health monitor for workflow deployments.

Set-up (To run Flowd and Etcd all in a Docker-Desktop k8s cluster)
==================================================================
See the `README.md` in examples/istio.

Set-up (To run Flowd and Etcd on your own Terminal)
==================================================

* Add `flowlib`, `flowd`, `flowctl`, and `healthd` to your Python path using the
  base directory of the prototype.  This is the same base directory that `flowctl`
  lives in itself.  For example:
  `export PYTHONPATH=.../rexflow:$PYTHONPATH`.
* In another shell, run the etc daemon.  This will require you to set a `GOPATH`,
  and add it's `bin` subdirectory to your `PATH`.  For example:
  ```zsh
  % export GOPATH=~/go
  % export PATH=$GOPATH/bin:$PATH
  % etcd
  ```
* In another shell, run the REXFlow daemon.  For example:
  ```zsh
  % python -m flowd
  2020-07-13 14:53:28,128|flowd|INFO|__main__.py:17|Starting flowd on port 9001...
  ```
* In yet another shell, run the health daemon.  For example:
  ```zsh
  % python -m healthd
     * Serving Flask app "healthd" (lazy loading)
     * Environment: production WARNING: This is a development server. Do not use it in a production deployment.
       Use a production WSGI server instead.
     * Debug mode: off
  2020-08-07 14:47:24,880|healthd|INFO|_internal.py:113| * Running on http://0.0.0.0:5050/ (Press CTRL+C to quit)
  ...
  ```
* You may optionally test your set-up using the `ps` command.  For example:
  ```zsh
  % python -m flowctl ps
  2020-08-07 14:59:36,347|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {}
  ```

*Note:* When you use the `istio` or `kubernetes` orchestrator with this strategy, you will run into some problems: the Flowd and Etcd both sit outside the cluster, so you will need to add your own Istio Gateway (an exercise left to the reader) to allow the Flowd to talk to services running inside your Docker-Desktop cluster (in order to get the Flow Instances to start). The services inside the cluster will have no way to talk to your Flowd (since it's running on your shell), so they will never tell Flowd that the Flow Instance has finished. However, running Flowd outside the cluster has the benefit of letting you use the `pdb` debugger, as well as letting you test changes without rebuilding a Docker image and kicking your pod.


Getting started (Potentially deprecated, recommended to see `examples/istio/README.md`)
===============

* (Optional) Create a BPMN XML document via a BPMN modeling tool (such as Zeebe
  modeler).  Otherwise, you can use one of the example diagrams.
* Create a *workflow deployment* using *apply*.  For example:
  ```zsh
  % python -m flowctl apply examples/calc/calcprocess.bpmn
  2020-07-13 15:48:52,857|flowctl|INFO|apply_action.py:55|Got response: 0, "Ok", {"CalcProcess": "CalcProcess-42e0680ac54a11ea8c8bacde48001122"}
  ```
  The tool will provide a workflow deployment ID, such as
  `CalcProcess-42e0680ac54a11ea8c8bacde48001122`.
* Create a *workflow_instance*, using *run*.  For example:
  ```zsh
  % python -m flowctl run example_ba583a10bbc311ea9f25faffc22d59be 42
  ```
  The tool will provide a workflow instance ID, such as
  `flow_47d8a3d4bbc411ea9f25faffc22d59be`.
* Query the state of a *workflow instance* using *ps*.  For example:
  ```zsh
  % python -m flowctl ps flow_47d8a3d4bbc411ea9f25faffc22d59be
  ```
* Eventually halt the workflow deployment using the *stop* verb.
  (Ensure state transition to `STOPPED`.)

Troubleshooting
===============

Once the workflow instance is complete, the result will be reported via this
same `ps` command.
