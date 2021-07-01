from flowlib.postgres_db_schema import RequestData, StateLog
from flowlib.quart_app import QuartApp
from quart import request
from datetime import datetime
from flowlib.config import get_kafka_config
import json
from confluent_kafka import Consumer
import sqlalchemy
from sqlalchemy import insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flowlib.executor import get_executor
from flowlib.config import POSTGRES_DB_URI, DEFAULT_NOTIFICATION_KAFKA_TOPIC

Base = declarative_base()
engine = sqlalchemy.create_engine(POSTGRES_DB_URI)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

# Kafka Setup

KAFKA_GROUP_ID = "workflow-kafka-consumer"
KAFKA_TOPIC = DEFAULT_NOTIFICATION_KAFKA_TOPIC
config = {
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
config.update(get_kafka_config())
kafka = Consumer(config)
kafka.subscribe([KAFKA_TOPIC])

# StateLogto run in the background and insert all
# kafka messages into the database


class StateLogger:
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
                if msg_dict["event_type"] == "ETCD_PUT":
                    query = insert(StateLog).values(instance_id=msg_dict["instance_id"],
                                                    timestamp=datetime.now(),
                                                    state=msg_dict["instance_state"],
                                                    workflow_id=msg_dict["workflow_id"])
                    engine.execute(query)
                if msg_dict["event_type"] == "REQUEST_SENT":
                    json_data = msg_dict['request_data']
                    query = "INSERT INTO "
                    query += "request_data (instance_id, timestamp, data, workflow_id, headers) "
                    query += "VALUES(%s, %s, %s, %s, %s);"
                    my_data = [msg_dict["instance_id"], datetime.now(),
                               json.dumps(json_data), msg_dict['workflow_id'],
                               json.dumps(msg_dict['request_headers'])]
                    engine.execute(query, my_data)
        except Exception as exn:
            import logging
            logging.exception("ooph", exc_info=exn)


class DBManager(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.manager = StateLogger()
        self.app.route('/instances/<instance_id>', methods=['GET'])(self.current_state)
        self.app.route("/instances", methods=['GET'])(self.instance_query)
        self.app.route('/instances/<instance_id>/running_time', methods=['GET'])(self.instance_time)
        self.app.route('/deployments', methods=['GET'])(self.deployments_query)
        self.app.route('/bpmn_traffic/<workflow_id>/<bpmn_id>', methods=['GET'])(self.bpmn_traffic)
    
    def deployments_query(self):
        args = dict(request.args)
        conditions = ""
        i = 0
        res = session.query(StateLog).filter_by(**args).all()
        workflow_ids= []
        for row in res:
            workflow_ids.append(row.workflow_id)
        workflow_ids = list(set(workflow_ids))
        return workflow_ids

    def bpmn_traffic(self, workflow_id, bpmn_id):
        args = {'X-Rexflow-Did':workflow_id,'X-Rexflow-Tid':bpmn_id}
        conditions = ""
        i = 0
        query_params = []
        res = []
        for i, itm in enumerate(args.keys()):
            if i == 0:
                conditions += "WHERE "
            conditions += " headers  ->> %s ="    # Formatting check if data.itm == args[itm]
            if i == len(args.keys())-1:
                conditions += "%s "
            else:
                conditions += "%s AND "
            query_params.append(itm)
            query_params.append(args[itm])
        query = "SELECT instance_id FROM request_data " + conditions + ";"
        resultproxy = engine.execute(query, query_params)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        for itm in a:
            if itm['instance_id'] not in res:
                res.append(itm['instance_id'])
        traffic_through = len(set(res))
        args = {'X-Rexflow-Did':workflow_id}
        conditions = ""
        i = 0
        query_params = []
        res = []
        for i, itm in enumerate(args.keys()):
            if i == 0:
                conditions += "WHERE "
            conditions += " headers  ->> %s ="    # Formatting check if data.itm == args[itm]
            if i == len(args.keys())-1:
                conditions += "%s "
            else:
                conditions += "%s AND "
            query_params.append(itm)
            query_params.append(args[itm])
        query = "SELECT instance_id FROM request_data " + conditions + ";"
        resultproxy = engine.execute(query, query_params)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        for itm in a:
            if itm['instance_id'] not in res:
                res.append(itm['instance_id'])
        traffic_total = len(set(res))
        return str(traffic_through*100/traffic_total) + "% of traffic goes through " + bpmn_id + " in " + workflow_id  + "\n"

    def instance_query(self):
        args = dict(request.args)
        conditions = ""
        i = 0
        query_params = []
        res = []
        for i, itm in enumerate(args.keys()):
            if i == 0:
                conditions += "WHERE "
            conditions += " data  ->> %s ="    # Formatting check if data.itm == args[itm]
            if i == len(args.keys())-1:
                conditions += "%s "
            else:
                conditions += "%s AND "
            query_params.append(itm)
            query_params.append(args[itm])
        query = "SELECT instance_id FROM request_data " + conditions + ";"
        resultproxy = engine.execute(query, query_params)
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

    def current_state(self, instance_id):
        query = "SELECT * FROM state_log WHERE instance_id=%s ORDER BY timestamp DESC LIMIT 1;"
        query_params = [instance_id]
        resultproxy = engine.execute(query, query_params)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        return str(a)

    def instance_time(self, instance_id):
        query = "SELECT * FROM state_log WHERE instance_id=%s ORDER BY timestamp DESC LIMIT 1;"
        query_params = [instance_id]
        resultproxy = engine.execute(query, query_params)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        latest_date = a[0]['timestamp']
        query = "SELECT * FROM state_log WHERE instance_id=%s ORDER BY timestamp ASC LIMIT 1;"
        query_params = [instance_id]
        resultproxy = engine.execute(query, query_params)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
        earliest = a
        earliest_date = a[0]['timestamp']
        if earliest[0]['state'] != 'COMPLETED':
            return "Instance is not completed yet"
        diff = latest_date - earliest_date
        return "Process " + str(instance_id) + " Took " + str(diff.microseconds) + "ms to run \n"

    def run(self):
        self.manager.start()
        super().run()

    def shutdown(self):
        self.manager.stop()


if __name__ == '__main__':
    app = DBManager(bind=f'0.0.0.0:5000')
    app.run()
