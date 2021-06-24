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
            P = round(ast.literal_eval(req_json['principal']),2) # Principle!
            R = round(ast.literal_eval(req_json['interest']),5)  # interest Rate!
            T = ast.literal_eval(req_json['term'])               # Term!

            dR     = R / 100.0     # interest rate as proper fraction
            mR     = dR / 12.0     # monthly interest rate
            mRp1   = mR + 1.0      # monthly interest rate plus 1.0
            mRp1eT = mRp1 ** T     # (monthly rate + 1) ^ term
            PMT    = round(P * (mR * mRp1eT) / (mRp1eT - 1.0), 2) # PayMenT!

            
            # build a TABLE data structure as per REXFLOW-215
            table = []
            TI, TP = 0.0, 0.0   # total interest, total payments

            B = P
            for month in range(int(T)):
                # payment = total monthly payment - (outstanding balance * (interest / 12))
                PI = round(B * mR, 2)                       # Principal Interest
                if B < PMT:
                    # this is the last payment
                    PP  = B
                    PMT = round(PI + PP, 2)
                    B   = 0.0
                else:
                    PP  = round(PMT - PI, 2)
                    B   = round(B - PP, 2)
                TI = round(TI + PI, 2)  
                TP = round(TP + PMT, 2)
                table.append([month+1, PMT, PP, PI, B])

            data = {"payment":PMT, "total_interest":TI, "total_payments":TP}
            data.update(req_json)
            data['table'] = {"heading":["Period", "Payment", "Principal", "Interest", "Balance"], "body": table}
            
            response = make_response(data, 200)
            for hdr in FORWARD_HEADERS:
                if hdr in request.headers:
                    response.headers[hdr] = request.headers[hdr]
            logging.info(f'content-length {response.calculate_content_length()} content-type {response.content_type}')
            logging.info(response)
        elif mode == 'amort-best-rate':
            # essentially "pick" a random interest rate between
            # 0.01 and 1.99
            random.seed(time.time())
            r = round( random.triangular(0.01,2.00), 2)
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
