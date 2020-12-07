# Start and Stop Events as a Service

This example demonstrates the capabilities of the start and stop event services, specifically:

1. Ability to start a WF Instance by making direct HTTP call to start service
2. Ability to publish to a Kafka topic after a WF Instance completes
3. Ability to start a WF Instance by listening to a Kafka topic

To run the example:

```
python -m flowctl apply a.bpmn
python -m flowctl apply b.bpmn

# wait for deployments to come up

# Now, make an http call to the start service of A.
# This just starts a WF Instance of A.
kubectl -n rexflow exec $(kubectl -nrexflow get po | grep flowd | cut -d ' ' -f1) -- curl -d '{}' -H "content-type: application/json" http://start-a-86f7e437.default:5000/


# This should show that the End Service of A has pushed an Event that triggers an Instance of the B WF to run
python -m flowctl ps


# We can still run A manually:
python -m flowctl run a '{}'

# We can also run just B manually:
python -m flwoctl run b '{}'
```