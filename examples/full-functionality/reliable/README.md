# Simple Example to Demonstrate Reliable WF
In a "reliable" workflow, the Envoy Proxies on the microservices communicate to each other through Kafka. This way, if one is down, it becomes easier to 

```
python -m flowctl apply reliable.bpmn
python -m flowctl run reliable '{}'
```

The workflow in `reliable.bpmn` is the same as the normal `examples/istio/istio-underpants.bpmn`, and should behave the same. A curious reader may interrogate the Kafka Topics used to communicate between the Workflows to see the communication flowing.