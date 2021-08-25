import os
import threading
from time import sleep

from flask import Flask, request, jsonify

import requests


WAIT_TIME = os.environ.get('WAIT_TIME', '10')
DEFAULT_METHODS = ['GET', 'PUT', 'POST']

server = Flask(__name__)


def get_wait_time():
    try:
        return int(WAIT_TIME)
    except:
        return 10


def wait_a_while():
    wait_time = get_wait_time()
    sleep(wait_time)
    return ''


def fail_miserably():
    os._exit(-1)


def always500():
    raise Exception('This is the error you are looking for.')


POISONS = {fn.__name__: fn for fn in [wait_a_while, fail_miserably, always500]}


for brand_name, fn in POISONS.items():
    server.route(f'/{brand_name}', methods=DEFAULT_METHODS)(fn)


def handle_poison(poison):
    if isinstance(poison, str):
        poison = [poison]
    elif not isinstance(poison, list):
        poison = []
    for brand in poison:
        if brand in POISONS:
            POISONS[brand]()


@server.route('/')
def healthcheck():
    return dict()


@server.route('/', methods=['PUT', 'POST'])
def serve():
    request_data = request.get_json(force=True, silent=True)
    if isinstance(request_data, dict) and 'poison' in request_data:
        poison = request_data['poison']
        handle_poison(poison)
    return jsonify(request_data)


def async_handler(request_data: dict):
    handle_poison(request_data.get('poison'))
    cb_result = requests.post(request_data['cb'], json=request_data)
    cb_result.raise_for_status()


@server.route('/async', methods=DEFAULT_METHODS)
def async_request():
    request_data = request.get_json(force=True, silent=True)
    if isinstance(request_data, dict) and 'cb' in request_data:
        thread = threading.Thread(target=async_handler, args=(request_data,))
        thread.start()
    return jsonify(request_data)


if __name__ == '__main__':
    server.run(host='0.0.0.0')
