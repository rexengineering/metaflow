# Spec for Namespacing and Heterogeneity

Due to Colt's Sunday-morning laziness regarding finding a better format, this spec will take the form of a Q/A.

## How does a user of the system decide which WF gets its own namespace?
The user may specify in the BPMN to do one of the following:
* Specify only a WF Template Id:
    * A namespace is created specifically for the WF (named after the `id` in the BPMN), and the WF is deployed into that namespace.
    * If no `id` is specified, then an error is thrown upon `flowctl apply`.
* Specify a pre-existing namespace:
    * The deployment is deployed into the specified pre-existing namespace.
    * The Services/Deployments/EnvoyFilters/ServiceAccounts all get an id hash appended to their name to prevent conflicts.

## Can we edit a WF deployment after it is applied?
Currently, no. We will not support editing a WF deployment after it is applied. In order to edit a WF Deployment, please create a new one and then delete the old one.

## When we deploy a WF to a shared namespace (eg default), how do we ensure no service names collide?
When deploying to a shared namespace, each k8s object gets a hash appended to its name. For example, if our WF Template calls for the creation of a Service `secret-sauce` and an EnvoyFilter `hijack-secret-sauce`, the Service gets applied as `secret-sauce-892c` and the EnvoyFilter gets applied as `hijack-secret-sauce-892c`. When we deploy to a non-shared namespace, the names of the k8s objects are not changed.

## Can a WF include calls to services that have already been deployed?
Yes. For example, we may commonly want to call the `locationlookup` service, and we don't want to have to manage our own separate deployment of it. In this case, the user just adds the annotation `preexisting: true` to the Task on the BPMN document.

## Can a WF include calls to a service that is deployed by another WF Template?
This behavior will not be supported. Consider the following scenario:

* WF Template `A` is deployed and creates service `foo`.
* WF Template `B` is deployed and calls the `foo` service deployed by `A`.
* WF Template `A` is Stopped/Deleted.

In this scenario, we'd have to be clever about keeping track of the reference count for the `foo` service.

## What identifiers does a WF have?

It is required for a user to specify a `id` for the Workflow by annotating the StartEvent in the BPMN Spec. That `id` is accessible by the `BPMNProcess.id` or the `Workflow.id`.