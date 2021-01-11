'''Test script to simulate someone from outside the REXFlow swimlane doing the following:
1. Reading an Event from Kafka
2. Doing some tasks in that agent's swim lane
3. Pushing another Event back into the REXFlow SwimLane using Kafka.

Used for the comprehensive test case.
'''
import json

from confluent_kafka import Consumer, Producer

KAFKA_HOST = "my-cluster-kafka-bootstrap.kafka:9092"
KAFKA_TOPIC_READ_1 = "comprehensive-test-throw-1"
KAFKA_TOPIC_WRITE_1 = "comprehensive-test-catch-1"
KAFKA_TOPIC_READ_2 = "comprehensive-test-throw-2"
KAFKA_TOPIC_WRITE_2 = "comprehensive-test-catch-2"
GROUP_ID = "comprehensive_external_swimlane"

consumer_1 = Consumer({
    'bootstrap.servers': KAFKA_HOST,
    'group.id': GROUP_ID,
    'auto.offset.reset': 'earliest'
})
consumer_1.subscribe([KAFKA_TOPIC_READ_1])

consumer_2 = Consumer({
    'bootstrap.servers': KAFKA_HOST,
    'group.id': GROUP_ID,
    'auto.offset.reset': 'earliest'
})
consumer_2.subscribe([KAFKA_TOPIC_READ_2])

producer = Producer({'bootstrap.servers': KAFKA_HOST})


def process_message(msg, write_topic):
    headers = dict(msg.headers())
    assert 'x-flow-id' in headers
    assert 'x-rexflow-wf-id' in headers
    payload = json.loads(msg.value().decode())
    payload['val'] *= 2
    producer.produce(write_topic, json.dumps(payload).encode(), headers=headers)
    producer.poll(0.1)


print("Comprehensive Test Kafka Daemon: Processing first set of event throws.", flush=True)
msg = consumer_1.poll(15)

processed = 0

while msg is not None:
    processed += 1
    process_message(msg, KAFKA_TOPIC_WRITE_1)
    msg = consumer_1.poll(10)
    producer.poll(0.1)

producer.flush()
print(f"Comprehensive Test Kafka Daemon: Processed {processed} messages!", flush=True)
print("Comprehensive Test Kafka Daemon: Processing second set of event throws.", flush=True)
msg = consumer_2.poll(15)

processed = 0

while msg is not None:
    processed += 1
    process_message(msg, KAFKA_TOPIC_WRITE_2)
    msg = consumer_2.poll(10)
    producer.poll(0.1)

producer.flush()
print(f"Comprehensive Test Kafka Daemon: Processed {processed} messages!", flush=True)
