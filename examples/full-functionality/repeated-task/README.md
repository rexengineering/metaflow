# Heterogeneous Microservices + Workflows

This example demonstrates the capability of our WF Engine to call the same (preexisting) task twice in the same Workflow.

NOTE: we do not yet support either:

1. Calling the same preexisting service on consecutive tasks.
2. Calling the same self-deployed service twice at all.

To run, first rebuild the `secret-sauce` container (such that it also has the `/biscuits` endpoint on it, for demo).

```
./inject_and_deploy.sh sauce.yaml

python -m flowctl apply repeated.bpmn

python -m flowctl run repeated '{}'

python -m flowctl ps -o | jq .
```
