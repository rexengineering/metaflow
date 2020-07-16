Architecture
============

This project contains three principle components:

* `flowlib` - This is a common library for both `flowctl` and `flowd`.  Contains
  important stuff including *protobuf* declarations, and client-server support
  code.
* `flowctl` - This is the primary command line interface to the proposed system.
* `flowd` - This is a prototype backend for the proposed system.

Getting started
===============

* (Optional) Create a BPMN XML document via a BPMN modeling tool (such as Zeebe
  modeler).  Otherwise, you can use one of the example diagrams.
* Add `flowlib`, `flowd`, `flowctl` to your Python path using the base directory
  of the prototype.  This is the same base directory that `flowctl` lives in
  itself.  For example:
  `export PYTHONPATH=.../rexflow/prototypes/jriehl:$PYTHONPATH`.
* In another shell, run the etc daemon.  For example:
  ```zsh
  # Set GOPATH and add its binaries to the PATH.
  % export GOPATH=~/go
  % export PATH=$GOPATH/bin:$PATH
  % etcd
  ```
* In another terminal, run the REXFlow daemon.  For example:
  ```zsh
  % python -m flowd
  2020-07-13 14:53:28,128|flowd|INFO|__main__.py:17|Starting flowd on port 9001...
  ```
* Create a *workflow deployment* using *apply*.  For example:
  ```zsh
  % python -m flowctl apply examples/calc/calcprocess.bpmn
  2020-07-13 15:48:52,857|flowctl|INFO|apply_action.py:55|Got response: 0, "Ok", {"CalcProcess": "CalcProcess-42e0680ac54a11ea8c8bacde48001122"}
  ```
  The tool will provide a workflow deployment ID, such as
  `CalcProcess-42e0680ac54a11ea8c8bacde48001122`.
* Create a *workflow_instance*, using *run*.  For example:
  ```zsh
  % python -m flowctl run example_ba583a10bbc311ea9f25faffc22d59be --args 42
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
