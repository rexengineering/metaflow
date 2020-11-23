from confluent_kafka.admin import AdminClient, NewTopic


a = AdminClient({'bootstrap.servers': 'my-cluster-kafka-bootstrap.kafka:9092'})
new_topics = [NewTopic(topic, num_partitions=3, replication_factor=1) for topic in ["colttopic"]]

fs = a.create_topics(new_topics)

for topic, f in fs.items():
    try:
        f.result()  # The result itself is None
        print("Topic {} created".format(topic))
    except Exception as e:
        print("Failed to create topic {}: {}".format(topic, e))
