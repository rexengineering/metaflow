'''
Defines a set of data connectors.
'''


import logging
from typing import Any, Callable, Collection, List, Mapping, NamedTuple, Optional

from . import constants, etcd_utils


class Connection(NamedTuple):
    component_id: str
    k8s_url: str
    method: Optional[str]


class ConnectorError(Exception):
    def __init__(self, *args, errors: Optional[List[Exception]]=None, **kws):
        super().__init__(*args, **kws)
        self.errors = errors


class Connector:
    def __init__(
        self,
        in_edges: Collection[Connection],
        out_edges: Collection[Connection],
        responders: Mapping[str, Callable[[str, Any], None]]
    ):
        self.in_edges = in_edges
        self.out_edges = out_edges
        self.responders = responders

    def is_valid(self, request: Any) -> bool:
        content_type: str = request.content_type
        valid = content_type == 'application/json'
        logging.info(f'Input content-type is {content_type} which is {"" if valid else "not "}supported.')
        return valid

    def _handle_input(self, _: Any) -> Optional[Any]:
        raise NotImplementedError('Overload me!')

    def _send_output(self, destination: Connection, response: Any) -> None:
        if destination.method is not None:
            method_name = destination.method.lower()
        else:
            method_name = 'None'
        responder = self.responders.get(method_name)
        if not responder:
            raise ValueError(f'Unsupported destination method: {method_name}')
        responder(destination.k8s_url, response)

    def handle_data(self, request: Any) -> None:
        errors = []
        output_opt = None
        try:
            output_opt = self._handle_input(request)
        except Exception as exn:
            logging.exception('Failed to handle client input.', exc_info=exn)
            errors.append(exn)
        if output_opt is not None:
            for out_edge in self.out_edges:
                try:
                    self._send_output(out_edge, output_opt)
                except Exception as exn:
                    logging.exception(f'Failed to output to {out_edge}', exc_info=exn)
                    errors.append(exn)
        if len(errors) > 0:
            raise ConnectorError(errors=errors)


class ParallelConnector(Connector):
    def __init__(
        self,
        in_edges: Collection[Connection],
        out_edges: Collection[Connection],
        responders: Mapping[str, Callable[[str, Any], None]],
        merge_mode: constants.Parallel.MergeModes,
    ):
        super().__init__(in_edges, out_edges, responders)
        self.merge_mode = merge_mode
        self.etcd = etcd_utils.get_etcd()

    def _merge_data_as_object(self):
        raise NotImplementedError()

    def _merge_data_as_array(self):
        raise NotImplementedError()

    def _merge_data_as_update(self):
        raise NotImplementedError()

    def _handle_input(self, request: Any) -> Optional[Any]:
        raise NotImplementedError('Lazy developer error!')
