# EVENT THROW

This example demonstrates a Workflow in which we throw an Event after the first task is completed, and do not go on to the second task until an Event is "caught".

In this example, the first Task throws an Event to the topic "stolenpants", which is also the topic upon which Event Catch listens. Therefore, the Workflow should behave identically to the Underpants example in `examples/istio`.

To run this, please do:

```
python -m flowctl apply events.bpmn

# Wait for the deployment to start RUNNING. If curious, watch pods in the `events` namespace.

python -m flowctl run events '{}'`.
python -m flowctl ps -o | jq .
```

A curious reader may edit the BPMN file `events.bpmn` such that the Catch Event listens to a different Kafka topic than the Throw Event publishes to. In order to get a WF Instance to "COMPLETE", such a curious reader will have to implement and run a small script of some sort that listens to events fired to the `stolenpants` queue, and then fires corresponding events to the queue specified by the curious reader's BPMN document.

Note: If you are one of these curious readers, you must also pass along the following headers with each message:

`X-Flow-Id`: WF Instance Id
`X-Rexflow-Wf-Id`: WF Id
`Content-Type`: Content Type (eg. `application/json`)