import logging
import os

from time import sleep

from flask import Flask, request, jsonify, make_response
from random import random

server = Flask(__name__)


@server.route('/')
def healthcheck():
    return jsonify()


@server.route('/', methods=['PUT', 'POST'])
def serve():
    mode = os.environ.get('SERVER_MODE')
    if mode == 'collect_people':
        return jsonify({"person1": "hong", 'person2': 'colt'})
    req = request.get_json(force=True, silent=True)
    if mode == 'fake-email' or mode == 'fake-email-2':
        return jsonify({"person_i_emailed": req['recipient']})
    elif mode == 'underpants-array':
        return jsonify(["andy b's underwear", "hong's underwear", "tyler's underwear"])
    elif mode == 'count-victims':
        print(req)
        print(type(req), flush=True)
        return jsonify({"victim_count": len(req)})
    return "who goes there"


@server.route('/whooppee_cushion', methods=['PUT', 'POST'])
def biscuits():
    return jsonify({'whooppee_cushion': 'in position'})


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
