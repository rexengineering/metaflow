from flask import Flask

app = Flask(__name__)

from . import routes  # noqa


# TODO: Investigate whether or not we should move the KafkaProducer to this file.
# # Then, spawn off a thread that calls .poll(0) on the producer every so often
# so that the callbacks for failed delivery may be called.
