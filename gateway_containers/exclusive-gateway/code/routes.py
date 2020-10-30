from code import app
from flask import request
import os
import requests


REXFLOW_XGW_JSONPATH = os.environ['REXFLOW_XGW_JSONPATH']
REXFLOW_XGW_OPERATOR = os.environ['REXFLOW_XGW_OPERATOR']
REXFLOW_XGW_COMPARISON_VALUE = os.environ['REXFLOW_XGW_COMPARISON_VALUE']
REXFLOW_XGW_TRUE_URL = os.environ['REXFLOW_XGW_TRUE_URL']
REXFLOW_XGW_FALSE_URL = os.environ['REXFLOW_XGW_FALSE_URL']

SPLITS = REXFLOW_XGW_JSONPATH.split('.')

@app.route('/', methods=['POST'])
def conditional():
    incoming_json = request.json
    value_to_compare = incoming_json  # we will whittle this down to an actual value
    comparison_result = False  # placeholder for scoping
    print(incoming_json)

    for split in SPLITS:
        if split in value_to_compare:
            value_to_compare = value_to_compare[split]

    default_val = int(REXFLOW_XGW_COMPARISON_VALUE) if type(value_to_compare) == int else REXFLOW_XGW_COMPARISON_VALUE
    if type(value_to_compare) in [int, str]:
        if REXFLOW_XGW_OPERATOR == '==':
            comparison_result = (value_to_compare == default_val)
        elif REXFLOW_XGW_OPERATOR == '<':
            comparison_result = (value_to_compare < default_val)
        elif REXFLOW_XGW_OPERATOR == '>':
            comparison_result = (value_to_compare > default_val)
        else:
            raise "invalid rexflow xgw comparison operator"
    else:
        # For now, if the path specified is not a terminal path, we will assume that
        # the comparison failed.
        # TODO: become more sophisticated.
        comparison_result = False

    url = REXFLOW_XGW_TRUE_URL if comparison_result else REXFLOW_XGW_FALSE_URL

    # TODO: How about some error handling right here...
    requests.post(url, json=incoming_json, headers={'x-flow-id': request.headers['x-flow-id']})
    return "The faith of knowing deep inside your heart, that Heaven holds"


@app.route('/', methods=['GET'])
def health():
    return "more than just some stars...Someone's up there watching over you"
