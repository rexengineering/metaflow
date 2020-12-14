from flask import Flask, request, jsonify


server = Flask(__name__)


@server.route('/')
def hello():
    return 'Hello world!'


@server.route('/', methods=['PUT', 'POST'])
def calc():
    request_data = request.get_json()
    return jsonify(list(map(lambda x: 2 * float(x) ** 2, request_data)))


@server.errorhandler(TypeError)
def handle_type_error(exception):
    server.logger.exception(exception)
    reply = jsonify([])
    reply.status_code = 400
    return reply


if __name__ == '__main__':
    server.run(host='0.0.0.0')
