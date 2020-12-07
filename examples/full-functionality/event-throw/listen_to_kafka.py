'''
This is to be run from within the k8s cluster.
'''
from confluent_kafka import Consumer


KAFKA_HOST = "my-cluster-kafka-bootstrap.kafka:9092"
KAFKA_TOPIC = "stolenpants"

kafka = Consumer({
    'bootstrap.servers': KAFKA_HOST,
    'group.id': "1234",
    'auto.offset.reset': 'earliest'
})

while True:
    msg = kafka.poll()
    print("Got a message!\n\nMessage Headers:", msg.headers())
    print("**")
    print("Message body:", msg.value())
