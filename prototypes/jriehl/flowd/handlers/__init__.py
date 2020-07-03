import json
import logging
import sys

from flowlib import flow_pb2

from . import handle_apply, handle_delete, handle_ps, handle_run, handle_start,\
    handle_stop


def handler_dispatch(command, request, context):
    logging.info(f'Received {request} in {context}.')
    try:
        handler = globals()[f'handle_{command}'].handler
    except KeyError:
        logging.error(f'Unable to handle {command} request: {request}')
        return {'error': f'could not find handler for {command} command'}
    try:
        internal_response = handler(request)
    except Exception as exn:
        result = flow_pb2.FlowdResult(
            status=-1, message=f'{type(exn).__name__}({",".join(exn.args)})'
        )
        logging.info('Traceback from unhandled exception.', exc_info=exn)
        logging.error(f'Unhandled exception coming from delegated handler: {result.message}')
        return result
    return flow_pb2.FlowdResult(
        status=0, message='Ok', data=json.dumps(internal_response)
    )
