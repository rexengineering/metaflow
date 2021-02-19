# Simple Example of Observable Real-Time Workflows
This example demonstrates a feature flag in which one may configure REXFlow to mirror all traffic in all Instances of a Workflow to some pre-determined URL. In this example, we deploy a service that pushes all incoming traffic to Kafka, and we shadow traffic to this service.

```
kubectl apply -nrexflow -f kafka-shadow.yaml
python -m flowctl apply traffic_shadow.bpmn
python -m flowctl run shadow '{}'
```
