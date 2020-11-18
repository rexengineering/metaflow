import logging
import os

from flask import Flask, request, jsonify, make_response
from random import random

server = Flask(__name__)


@server.route('/')
def healthcheck():
    return jsonify()


@server.route('/', methods=['PUT', 'POST'])
def serve():
    mode = os.environ.get('SERVER_MODE')
    if mode == 'collect':
        if random() > 0.5:
            response = jsonify({'underpants': 'Collected.'})
        else:
            response = jsonify({"underpants": "Collected."})
    else:
        response = request.get_json(force=True, silent=True)
        if response is not None:
            logging.info(response)
            if mode == 'secret-sauce':
                response['sauce'] = 'Applied.'
            elif mode == 'profit':
                response['cashflow'] = 'Positive!'
            else:
                response = make_response('Server improperly configured!\n', 500)
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
    server.run(host='0.0.0.0')
