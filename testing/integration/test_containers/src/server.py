import logging
import os

from flask import Flask, request, jsonify
from random import random

server = Flask(__name__)


@server.route('/')
def healthcheck():
    return jsonify()


@server.route('/', methods=['PUT', 'POST'])
def serve():
    mode = os.environ.get('SERVER_MODE')
    mode = mode[:mode.find('-')]
    response = request.get_json(force=True, silent=True)

    if mode == 'collect':
        response = jsonify({'underpants': 'Collected.'})

    elif mode == 'sauce':
        response['sauce'] = 'Applied.'

    elif mode == 'profit':
        response['cashflow'] = 'Positive!'

    elif mode == 'increment':
        response['val'] += 1

    elif mode == 'decrement':
        response['val'] -= 1

    elif mode == 'unreliablesauce':
        assert random() > 0.5
        response['sauce'] = 'Applied.'

    elif mode == 'orz':
        response['cashflow'] = 'Orz'

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
