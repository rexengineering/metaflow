# Making sense of the BPMN Example Files

Prerequisite: Read and understand `README.md`. This file explains what each .bpmn file demonstrates, not how to use them.

### Run a simple 1-step workflow

`simple.bpmn`

### Run a simple 3-step workflow

`istio-underpants.bpmn`

### Run underpants and publish to the `stolenpants` queue

`throw.bpmn`

### Demo exclusive gateway

`conditional.bpmn`. Note that I've also changed the `collect` service to randomly choose between returning "What's going on" and returning "Underpants: Collected." If the underpants are collected, then the flow completes as in `istio-underpants.bpmn`. Else, execution halts.

### Demo Calling pre-existing services

`heterogeneous-underpants.bpmn`. Make sure to also `istioctl kube-inject` and deploy the `sauce.yaml` file into a namespace called `my-ns` for this to work.

### Simple Events Demo

Run `python catch_daemon.py` in a terminal, and apply `events.bpmn`. When you run `events.bpmn` you should see something in `catch_daemon.py`.

### Complicated Events Demo

Run `python catch_daemon.py` in a terminal and apply `theforce.bpmn`. When you run the flow, you should also see `catch_daemon.py`. If you say that the type of sauce is `applied`, then you will profit.