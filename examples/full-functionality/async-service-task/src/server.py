import logging
import os

from pprint import pprint
import threading
import requests

from flask import Flask, request, jsonify

server = Flask(__name__)


@server.route('/')
def healthcheck():
    return jsonify()


def make_call(url):
    print("making call to ", url, flush=True)
    requests.post(url, json={"The Force": "With Us."})


@server.route('/', methods=['PUT', 'POST'])
def serve():
    print("hi")
    data = request.get_json()
    print("got data:")
    pprint(data)
    timer = threading.Timer(4, lambda: make_call(data['callback_url']))
    print("started timer", flush=True)
    timer.start()
    return jsonify({"status": "acceptedasdf"}, 202)


@server.route('/jedi', methods=['POST'])
def jedi():
    data = request.get_json()
    payload = {}
    if data['jedi'] in ['obiwan', 'anakin']:
        payload = {'lightsaber': 'blue'}
    elif data['jedi'] == 'mace':
        payload = {'lightsaber': 'purple'}
    else:
        payload = {'lightsaber': 'green'}

    def make_jedi_call():
        requests.post(data['callback_url'], json=payload)
    timer = threading.Timer(3, make_jedi_call)
    timer.start()
    return jsonify({"status": "accepted"}, 202)

@server.route('/echo', methods=['POST'])
def echo():
    print("hehe I got called:", request.get_json(), flush=True)
    return "200"


@server.errorhandler(TypeError)
def handle_type_error(exception):
    server.logger.exception(exception) # pylint: disable=no-member
    reply = jsonify([])
    reply.status_code = 400
    return reply


if __name__ == '__main__':
    logging.info('Starting the Force server')
    server.run(host='0.0.0.0')
