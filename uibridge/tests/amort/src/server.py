import ast
import logging
import os
import random
import time

from time import sleep

from flask import Flask, request, jsonify, make_response

server = Flask(__name__)
# SERVER_MODES 
# amort-calc      - calculate the amortization table
# amort-best-rate - research the best rate

FORWARD_HEADERS = [
    'x-request-id',
    'x-b3-traceid',
    'x-b3-spanid',
    'x-b3-parentspanid',
    'x-b3-sampled',
    'x-b3-flags',
    'x-ot-span-context',
]

@server.route('/')
def healthcheck():
    return jsonify({'sokay?':'s\'allright'})

@server.route('/', methods=['PUT', 'POST'])
def serve():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    mode     = os.environ.get('SERVER_MODE')
    req_json = request.get_json(force=True, silent=False)
    if req_json is not None:
        logger.info(request.headers)
        logger.info(req_json)

        if mode == 'amort-calc':
            P = round(ast.literal_eval(req_json['principal']),2)
            R = round(ast.literal_eval(req_json['interest']),5)
            T = ast.literal_eval(req_json['term'])

            dR     = R / 100.0        # interest rate as proper fraction
            mR     = dR / 12.0     # monthly interest rate
            mRp1   = mR + 1.0
            mRp1xT = mRp1 ** T
            PMT    = round(P / ((mRp1xT-1.0)/(mR * mRp1xT)), 2)

            data = {"payment":PMT}
            data.update(req_json)
            
            table = {}

            B = P
            for month in range(int(T)):
                # payment = total monthly payment - (outstanding balance * (interest / 12))
                PI = round(B * mR, 2)
                PP = round(PMT - PI, 2)
                B  = round(B - PP, 2)
                table[month+1] = [PP, PI, B]
                if B < PMT:
                    PMT = B
            data["table"] = table
            response = make_response(data, 200)
            for hdr in FORWARD_HEADERS:
                if hdr in request.headers:
                    response.headers[hdr] = request.headers[hdr]
            logging.info(f'content-length {response.calculate_content_length()} content-type {response.content_type}')
            logging.info(response)
        elif mode == 'amort-best-rate':
            # essentially "pick" a random interest rate between
            random.seed(time.time())
            r = round( random.triangular(0.1,12.0), 2)
            req_json['interest'] = str(r)
            logger.info(req_json)
            response = make_response(req_json, 200)
        else:
            response = make_response(f'Unknown server mode {mode}', 400)
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
    logging.info(f'Starting server for {mode}')
    server.run(host='0.0.0.0')
