from flowlib.quart_app import QuartApp
from quart import request, jsonify
from datetime import datetime
from flowlib.config import get_kafka_config
import json
from confluent_kafka import Consumer
from flowlib.executor import get_executor
from flowlib.constants import flow_result

# Kafka Setup
KAFKA_GROUP_ID = "workflow-kafka-consumer"
KAFKA_TOPIC = "" #New Kafka topicc
config = {

        'group.id': KAFKA_GROUP_ID,

        'auto.offset.reset': 'earliest'

    }
config.update(get_kafka_config())
kafka = Consumer(config)
# kafka.subscribe([KAFKA_TOPIC])


class DataRouter:
    def __init__(self):
        self.executor = get_executor()
        self.running = True

    def start(self):
        self.executor.submit(self)

    def stop(self):
        self.running = False
    def __call__(self):
        try:
            while True:
                if not self.running:
                    break
                msg = kafka.poll(1)   # Get Messages
                if msg is None:
                    continue
                if msg.error():
                    continue
                msg_dict = json.loads(msg.value().decode())
                #Salesforce pushing handler

        except Exception as exn:
            import logging
            logging.exception("ooph", exc_info=exn)


class DataManager(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = DataRouter()
        self.app.route('/', methods=['GET'])(self.healthcheck)

    def healthcheck(self):
        return jsonify(flow_result(0, "Ok."))
        

if __name__ == '__main__':
    app = DataManager(bind=f'0.0.0.0:5001')
    app.run()