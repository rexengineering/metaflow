from sqlalchemy.engine import result
from flowlib.postgres_db_schema import request_data, state_log
from flowlib.quart_app import QuartApp
from quart import request
from datetime import datetime
from sqlalchemy.ext import declarative
from flowlib.config import get_kafka_config
import os
import json
from confluent_kafka import Consumer
import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flowlib.executor import get_executor
from flowlib.config import POSTGRES_DB_URI

Base = declarative_base()
engine = sqlalchemy.create_engine(POSTGRES_DB_URI)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

#Kafka Setup
KAFKA_GROUP_ID = "workflow-kafka-consumer"
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "rexflow-all-traffic")
config = {
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
config.update(get_kafka_config())
kafka = Consumer(config)
kafka.subscribe([KAFKA_TOPIC])

#State_log to run in the background and insert all kafka messages into the database
class State_Log:
    def __init__(self):
        self.executor = get_executor()
        self.running = True
    
    def start(self):
        self.executor.submit(self)
    
    def stop(self):
        self.running = False
    
    def __call__(self):
        while True:
            if not self.running:
                break
            msg = kafka.poll(1)    # Get Messages
            if msg is None:
                continue
            if msg.error():
                continue
            msg_dict = json.loads(msg.value().decode()) # Turn message into dict formate
            if msg_dict["event_type"] == "ETCD_PUT": # If the message is an ETCD_PUT we insert it into the state logs since it signals as state change so we store in state_logs
                engine.execute(insert(state_log).values(instance_id = msg_dict["instance_id"], timestamp = datetime.now(), state = msg_dict["instance_state"], workflow_id = msg_dict["workflow_id"]))
            if msg_dict["event_type"] == "REQUEST_SENT": # If the message is a request_sent it contains the info sent by the envoy proxy so we store it in request_data
                json_data = msg_dict['request_data']
                query = "INSERT INTO request_data (instance_id, timestamp, data, workflow_id, headers) VALUES(%s, %s, %s, %s, %s);"
                my_data = [msg_dict["instance_id"], datetime.now(), json.dumps(json_data), msg_dict['workflow_id'], json.dumps(msg_dict['request_headers'])]
                engine.execute(query, my_data)


class DB_Manager(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = State_Log()
        self.app.route('/<instance_id>', methods=['GET'])(self.latest_id)
        self.app.route("/instances", methods=['GET'])(self.instance_query)
    
    def instance_query(self):
        args = dict(request.args)
        conditions = ""
        i = 0
        my_data = []
        res = []
        for itm in args.keys():
            if i == 0:
                conditions += "WHERE "
            conditions += " data  ->> %s ="    # Formatting check if data.itm == args[itm]
            if i == len(args.keys())-1:
                conditions += "%s "
            else:
                conditions += "%s AND "
            i += 1
            my_data.append(itm)
            my_data.append(args[itm])
        if conditions != "":
            query = "SELECT instance_id FROM request_data " + conditions + ";"
            resultproxy = engine.execute(query, my_data)
            d, a = {}, []
            for rowproxy in resultproxy:
                # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
                for column, value in rowproxy.items():
                    # build up the dictionary
                    d = {**d, **{column: value}}
                a.append(d)
            for itm in a:
                res.append(itm['instance_id'])
            res = list(set(res))
        return res
        

    
    def latest_id(self, instance_id):
        query = "SELECT * FROM state_logs WHERE instance_id=%s ORDER BY timestamp DESC LIMIT 1;" # Find the latest state for an instance_id
        my_data = [instance_id]
        resultproxy = engine.execute(query, my_data)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        return str(a)
    
    def run(self):
        self.manager.start()
        super().run()
    
    def shutdown(self):
        self.manager.stop()

if __name__ == '__main__':
    app = DB_Manager(bind=f'0.0.0.0:5000')
    app.run()
