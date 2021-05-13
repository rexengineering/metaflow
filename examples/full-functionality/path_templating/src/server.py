import logging
import os

from time import sleep

from flask import Flask, request, jsonify, make_response
from random import random

server = Flask(__name__)


@server.route('/')
def healthcheck():
    return jsonify()


@server.route('/coworker/<coworker>/favorite-food', methods=['POST'])
def serve(coworker):
    food = "McDonald's"
    if coworker == 'Gary':
        food = "Tumble 22"
    elif coworker == 'Andrew':
        food = "Chick Fil A"
    elif coworker == 'Colt':
        food = "Cane's"
    return jsonify({
        'coworker_name': coworker,
        'favorite_food': food,
    })


@server.errorhandler(TypeError)
def handle_type_error(exception):
    server.logger.exception(exception) # pylint: disable=no-member
    reply = jsonify([])
    reply.status_code = 400
    return reply


if __name__ == '__main__':
    logging.info(f'Starting server for path templating demo')
    server.run(host='0.0.0.0')
