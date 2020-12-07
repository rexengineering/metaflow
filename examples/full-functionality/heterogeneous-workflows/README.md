# Heterogeneous Microservices + Workflows

This example demonstrates the capability of our WF Engine to use a pre-existing microservice as a ServiceTask in one or more workflows. To run this example, you must first deploy the `secret-sauce` services to the default namespace and inject the correct istio-proxy. Next, we apply two Workflow Templates, which both use some combination of the Services we just deployed:

1. The `h-pants` workflow (short for heterogeneous-pants) deploys its own `collect` pod; and calls its `collect` service and then the shared `secret-sauce`service in that order.
2. The `h2-pants` workflow deploys its own `collect` service and `profit` service; and calls its `collect` service, the shared `secret-sauce` service, and its own `profit` service in that order.

To run this example, do:

```
kubectl config set-context --current --namespace=default
./inject_and_deploy.sh sauce.yaml
python -m flowctl apply heterogeneous-underpants.bpmn
python -m flowctl apply heterogeneous-underpants2.bpmn

# See that h-pants deploys its own `collect` service:
kubectl get po -nh-pants

# See that h2-pants deploys its own `collect` and `profit` services:
kubectl get po -h2-pants


# In another shell, watch the logs of the `secret-sauce` so that you can be convinced
# that both WF's use it:
kubectl -ndefault logs -f $(kubectl get po -ndefault | grep secret-sauce | cut -d ' ' -f1) -c secret-sauce

# Run both WF's:
python -m flowctl run h-pants '{}'
python -m flowctl run h2-pants '{}'

# You should see that h-pants doesn't profit, but h2-pants *does* profit.
python -m flowctl ps
```

