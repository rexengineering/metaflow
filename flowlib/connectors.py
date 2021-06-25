'''Defines a set of data connectors.
'''

import logging
from typing import Any, Callable, Collection, List, Mapping, NamedTuple, Optional, Tuple

from . import constants, stores
from .constants import Headers, WorkflowInstanceKeys


class Connection(NamedTuple):
    component_id: str
    k8s_url: str
    metadata: Mapping[str, Any]


class ConnectorError(Exception):
    def __init__(self, *args, errors: Optional[List[Exception]]=None, **kws):
        super().__init__(*args, **kws)
        self.errors = errors


class Connector:
    def __init__(
        self,
        in_edges: Collection[Connection],
        out_edges: Collection[Connection],
        responders: Mapping[str, Callable[[str, Any], None]],
    ):
        self.in_edges = in_edges
        self.out_edges = out_edges
        self.responders = responders

    def is_valid(self, request: Any) -> bool:
        content_type: str = request.content_type
        valid = content_type == 'application/json'
        logging.info(f'Input content-type is {content_type} which is {"" if valid else "not "}supported.')
        if valid and Headers.X_HEADER_FLOW_ID not in request.headers:
            logging.error(f'Input headers do not contain an instance ID.')
            return False
        return valid

    def _handle_input(self, _: Any) -> Optional[Any]:
        raise NotImplementedError('Overload me!')

    def _send_output(self, destination: Connection, response: Any) -> None:
        if 'method' in destination.metadata:
            method_name = destination.metadata['method'].lower()
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
    class StoreKeys(NamedTuple):
        count: str
        value: str

    def __init__(
        self,
        gateway_id: str,
        in_edges: Collection[Connection],
        out_edges: Collection[Connection],
        responders: Mapping[str, Callable[[str, Any], None]],
        merge_mode: constants.Parallel.MergeModes,
        store: stores.KVStore[Any],
    ):
        super().__init__(in_edges, out_edges, responders)
        self.gateway_id = gateway_id
        self.merge_mode = merge_mode
        self.store = store

    def is_valid(self, request: Any) -> bool:
        valid = super().is_valid(request)
        if valid and self.merge_mode == constants.Parallel.MergeModes.UPDATE:
            return isinstance(request.get_json(), dict)
        return valid

    def _merge_data_as_object(self, stored: Mapping[str, Any], incoming: Any) -> Mapping[str, Any]:
        result = dict(stored)
        result[f'result{len(result)}'] = incoming
        return result

    def _merge_data_as_array(self, stored: List[Any], incoming: Any) -> List[Any]:
        result = stored.copy()
        result.append(incoming)
        return result

    def _merge_data_as_update(self, stored: Mapping[str, Any], incoming: Mapping[str, Any]) -> Mapping[str, Any]:
        result = dict(stored)
        result.update(incoming)
        return result

    def _make_keys(self, instance_id: str) -> StoreKeys:
        return ParallelConnector.StoreKeys(
            WorkflowInstanceKeys.pgw_count_key(instance_id, self.gateway_id),
            WorkflowInstanceKeys.pgw_value_key(instance_id, self.gateway_id),
        )

    def _get_stored(self, keys: StoreKeys) -> Tuple[int, Any]:
        count = self.store.get(keys.count)
        if count is None:
            count = 0
            value = self.empty_value
        else:
            value = self.store[keys.value]
        return count, value

    def _set_stored(self, keys: StoreKeys, counter: int, value: Any):
        self.store[keys.count] = counter
        self.store[keys.value] = value

    def _handle_input(self, request: Any) -> Optional[Any]:
        result = None
        in_edge_count = len(self.in_edges)
        if in_edge_count > 1:
            instance_id = request.headers[Headers.X_HEADER_FLOW_ID]
            keys = self._make_keys(instance_id)
            stored_count, stored_value = self._get_stored(keys)
            if self.merge_mode == constants.Parallel.MergeModes.OBJECT:
                new_value = self._merge_data_as_object(stored_value, request.get_json())
            elif self.merge_mode == constants.Parallel.MergeModes.ARRAY:
                new_value = self._merge_data_as_array(stored_value, request.get_json())
            elif self.merge_mode == constants.Parallel.MergeModes.UPDATE:
                new_value = self._merge_data_as_update(stored_value, request.get_json())
            else:
                raise RuntimeError(f'Unhandled merge mode: {self.merge_mode}')
            stored_count += 1
            if stored_count == len(self.in_edges):
                result = new_value
                self._set_stored(keys, 0, self.empty_value)
            else:
                self._set_stored(keys, stored_count, new_value)
        else:
            result = request.get_json()
        return result

    @property
    def empty_value(self):
        return {} if self.merge_mode != constants.Parallel.MergeModes.ARRAY else []
