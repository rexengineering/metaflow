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

* (Optional) Create a BPMN XML document titled `example.bpmn` via a BPMN 
  modeling tool (such as Zeebe modeler).
* Add `flowlib`, `flowd`, `flowctl` to your Python path using the base directory
  of the prototype.  This is the same base directory that `flowctl` lives in
  itself.  For example: 
  `export PYTHONPATH=.../rexflow/prototypes/jriehl:$PYTHONPATH`.
* Create a *workflow deployment*, using `python -m flowctl apply example.bpmn`.
  The tool will provide a workflow deployment ID, such as
  `example_ba583a10bbc311ea9f25faffc22d59be`.
* Create a *workflow_instance*, using
  `python -m flowctl run example_ba583a10bbc311ea9f25faffc22d59be --args 42`.
  The tool will provide a workflow instance ID, such as
  `flowid_47d8a3d4bbc411ea9f25faffc22d59be`.
* Query the state of a *workflow instance* using
  `python -m flowctl ps flowid_47d8a3d4bbc411ea9f25faffc22d59be`.

Once the workflow instance is complete, the result will be reported via this
same `ps` command.
