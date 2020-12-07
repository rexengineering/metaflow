# EVENT THROW

This example demonstrates throwing an event midway through a Workflow. After we "collect" the underpants, we publish to a kafka topic called `stolenpants`.

To run this, do a `python -m flowctl apply throw.bpmn`, and `python -m flowctl run throw '{}'`.

To see the messages thrown by the events, just run the following command:

```kubectl run -nkafka kafka-consumer -ti --image=strimzi/kafka:latest-kafka-2.4.0 --rm=true --restart=Never -- bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic stolenpants --from-beginning```