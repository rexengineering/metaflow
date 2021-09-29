"""Daemon that publishes all events relating to a workflow to a specified
Kafka topic.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from threading import Thread
from typing import Callable, Iterable, Optional

from etcd3.client import Etcd3Client
from etcd3.events import PutEvent
from confluent_kafka import Producer
from quart import request, jsonify

from flowlib.config import (
    get_kafka_config,
    WORKFLOW_PUBLISHER_LISTEN_PORT,
)
from flowlib.constants import (
    flow_result,
    WorkflowInstanceKeys,
    split_key,
    Headers,
)
from flowlib.etcd_utils import get_dict_from_prefix, get_etcd
from flowlib.executor import get_executor
from flowlib.flowpost import FlowPost
from flowlib.quart_app import QuartApp


class MessageTypes:
    ETCD_PUT = "ETCD_PUT"
    ETCD_DELETE = "ETCD_DELETE"
    REQUEST_SENT = "REQUEST_SENT"


class EtcdInstanceWatcher:
    def __init__(self, etcd: Etcd3Client, kafka: Producer, workflow_id: str, kafka_topic: str):
        self._etcd: Etcd3Client = etcd
        self._kafka: Producer = kafka
        self._workflow_id: str = workflow_id
        self._kafka_topic: str = kafka_topic
        self._cancel: Optional[Callable] = None
        self._watch_iter = None
        self._executor: ThreadPoolExecutor = get_executor()
        self._etcd_prefix = f'{WorkflowInstanceKeys.ROOT}/{self._workflow_id}'
        

    def start(self):
        print("starting", flush=True)
        logging.info(f"Creating watch_iter on etcd for prefix {self._etcd_prefix}.")
        self._watch_iter, self._cancel = self._etcd.watch_prefix(self._etcd_prefix)
        self._executor.submit(self)

    def __call__(self):
        for event in self._watch_iter:
            try:
                self._process_event(event)
                logging.info("processed event successfully.")
            except Exception as exn:
                logging.exception(
                    f'Failed processing event',
                    exc_info=exn,
                )

    def _process_event(self, event):
        key = event.key.decode('utf-8')
        if not key.endswith('/state'):
            return
        instance_id = WorkflowInstanceKeys.iid_from_key(key)
        workflow_id, _ = split_key(instance_id)
        assert workflow_id == self._workflow_id
        instance_state = event.value.decode('utf-8')

        # send metadata in both the payload and the message headers as well for now.
        headers = {
            'instance_id': instance_id,
            'workflow_id': workflow_id,
            'event_type': MessageTypes.ETCD_PUT if isinstance(event, PutEvent) else MessageTypes.ETCD_DELETE,
            'content-type': 'application/json',
        }
        body_dict = {
            "instance_data": get_dict_from_prefix(
                prefix=f'{self._etcd_prefix}/{instance_id}',
                value_transformer=lambda bstr: bstr.decode('utf-8'),
            ),
            "instance_state": instance_state,
            **headers,
        }
        logging.info(
            f"Instance {instance_id} in state {instance_state}"
        )
        self._send_message(json.dumps(body_dict), headers)

    def _send_message(self, body: str, headers: dict):
        self._kafka.produce(
            self._kafka_topic,
            body,
            headers=headers,
        )
        logging.info(
            f"Successfully sent message."
        )

    def stop(self):
        self._cancel()


class WorkflowPublisher(QuartApp):
    def __init__(self, kafka: Producer, etcd: Etcd3Client, workflow_id, kafka_topic, **kws):
        super().__init__(__name__, **kws)
        self._etcd: Etcd3Client = etcd
        self._kafka: Producer = kafka
        self._workflow_id: str = workflow_id
        self._kafka_topic: str = kafka_topic
        self.manager = EtcdInstanceWatcher(
            self._etcd,
            self._kafka,
            self._workflow_id,
            self._kafka_topic,
        )

        self.app.route('/', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['POST'])(self.fire_event)

    def health_check(self):
        self._etcd.get("MayTheForceBeWithUs")
        self._kafka.poll()
        return jsonify(flow_result(0, ""))

    async def fire_event(self):
        data = await request.data
        message_headers = {
            'instance_id': request.headers[Headers.X_HEADER_FLOW_ID],
            'workflow_id': self._workflow_id,
            'event_type': MessageTypes.REQUEST_SENT,
            'content-type': 'application/json',
        }
        payload = {
            'request_data': FlowPost.jsonify_or_encode_data(data),
            'request_headers': dict(request.headers),
            **message_headers,
        }
        self.manager._send_message(json.dumps(payload), message_headers)
        return jsonify(flow_result(0, "Saved."))

    def run(self):
        self.manager.start()
        # now bring up the web server (this call blocks)
        super().run()

    def _shutdown(self):
        self.manager.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    etcd = get_etcd()
    print("getting kafka", flush=True)
    kafka = Producer(get_kafka_config())
    print("got kafka", flush=True)
    kafka_topic = os.environ['REXFLOW_PUBLISHER_KAFKA_TOPIC']
    workflow_id = os.environ['REXFLOW_PUBLISHER_WORKFLOW_ID']
    logging.info(
        f"Sending events for wf {workflow_id} to topic {kafka_topic}"
    )

    app = WorkflowPublisher(
        kafka,
        etcd,
        workflow_id,
        kafka_topic,
        bind=f'0.0.0.0:{WORKFLOW_PUBLISHER_LISTEN_PORT}'
    )
    app.run_serve()
