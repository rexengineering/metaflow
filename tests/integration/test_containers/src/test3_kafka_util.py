'''Test script to simulate someone from outside the REXFlow swimlane doing the following:
1. Reading an Event from Kafka
2. Doing some tasks in that agent's swim lane
3. Pushing another Event back into the REXFlow SwimLane using Kafka.
'''
import json

from confluent_kafka import Consumer, Producer

KAFKA_HOST = "my-cluster-kafka-bootstrap.kafka:9092"
KAFKA_TOPIC_READ = "test3_throw"
KAFKA_TOPIC_WRITE = "test3_catch"
GROUP_ID = "test3_external_swimlane"

consumer = Consumer({
    'bootstrap.servers': KAFKA_HOST,
    'group.id': GROUP_ID,
    'auto.offset.reset': 'earliest'
})
producer = Producer({'bootstrap.servers': KAFKA_HOST})


def process_message(msg):
    headers = dict(msg.headers())
    assert 'x-flow-id' in headers
    assert 'x-rexflow-wf-id' in headers
    payload = json.loads(msg.value().decode())
    payload['val'] *= 2
    producer.produce(KAFKA_TOPIC_WRITE, json.dumps(payload).encode(), headers=headers)
    producer.poll(0.1)


consumer.subscribe([KAFKA_TOPIC_READ])
print("Test3 Event Processing daemon: starting to poll", flush=True)
msg = consumer.poll(15)

processed = 0

while msg is not None:
    processed += 1
    process_message(msg)
    msg = consumer.poll(10)
    producer.poll(0.1)

producer.flush()
print(f"Test3 Event Processing daemon: done processing {processed} messages!", flush=True)
