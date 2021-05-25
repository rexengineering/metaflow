import logging
import os

from time import sleep

from flask import Flask, request, jsonify, make_response
from random import random

server = Flask(__name__)

SERVER_MODE = os.environ.get('SERVER_MODE')

@server.route('/')
def healthcheck():
    return jsonify({'hello':'world'})

@server.route('/', methods=['PUT', 'POST'])
def serve():
    response = request.get_json(force=True, silent=True)
    response['mode'] = mode
    if response is not None:
        logging.info(response)
    else:
        response = make_response('Bad input!\n', 400)
    return response

@server.errorhandler(TypeError)
def handle_type_error(exception):
    server.logger.exception(exception) # pylint: disable=no-member
    reply = jsonify([])
    reply.status_code = 400
    return reply


if __name__ == '__main__':
    mode = os.environ.get('SERVER_MODE')
    sleep_time = int(os.environ.get('SLEEP_TIME'))
    logging.info(f'Starting server for {mode} with sleep time {sleep_time}')
    server.run(host='0.0.0.0')
