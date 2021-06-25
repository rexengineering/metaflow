'''Unit test harness for REXFlow logic layer.
'''
from flowlib.constants import Headers
import json
from typing import Any, Callable, Iterable, List, Mapping, Optional, Tuple

from pydantic import BaseModel, Field


class GenericComponent:
    '''Base class for test harness components.
    '''
    def add_source(self, source: 'GenericComponent') -> None:
        pass

    def add_target(self, target: 'GenericComponent') -> None:
        pass

    def receive(self, payload: Any) -> Any:
        raise NotImplementedError('Overload me!')

    def send(self, target: 'GenericComponent', payload: Any) -> Any:
        raise NotImplementedError('Overload me!')


class GenericUpstream(GenericComponent):
    '''A generic upstream data producer.
    '''
    def __init__(self, target: Optional[GenericComponent] = None):
        self.target = target
        self.log: List[Tuple[GenericComponent, Any, Any]] = []

    def add_target(self, target: GenericComponent) -> None:
        if self.target is not None:
            raise ValueError('GenericUpstream may only have one target.')
        self.target = target

    def receive(self, payload: Any) -> Any:
        assert self.target is not None, 'GenericUpstream instances must have a target'
        return self.send(self.target, payload)

    def send(self, target: GenericComponent, payload: Any) -> Any:
        response = target.receive(payload)
        self.log.append((target, payload, response))
        return response


class GenericDownstream(GenericComponent):
    '''A generic downstream data consumer.
    '''
    def __init__(self, response: Any = True):
        self.received = []
        self.response = response

    def receive(self, payload: Any) -> Any:
        self.received.append(payload)
        return self.response

    def send(self, *_):
        raise NotImplementedError('GenericDownstream.send() should not be called.')


ReceiverType = Callable[[Any], Any]
TransmitterType = Callable[[GenericComponent, Any], Any]
TransceiverFactoryType = Callable[[
    Iterable[GenericComponent], TransmitterType, Iterable[GenericComponent]
], ReceiverType]


class TestComponent(GenericComponent):
    '''Adapter between a concrete logical connector and the test harness.
    '''
    def __init__(
        self,
        transceiver_factory: TransceiverFactoryType,
        sources: Optional[Iterable[GenericComponent]] = None,
        targets: Optional[Iterable[GenericComponent]] = None,
    ) -> None:
        sources = [] if sources is None else list(sources)
        targets = [] if targets is None else list(targets)
        self.sources = sources
        self.targets = targets
        self.transceiver_factory = transceiver_factory
        self.transceiver = transceiver_factory(sources, self.send, targets)

    def add_source(self, source: GenericComponent) -> None:
        if source not in self.sources:
            self.sources.append(source)
            self.transceiver = self.transceiver_factory(self.sources, self.send, self.targets)

    def add_target(self, target: GenericComponent) -> None:
        if target not in self.targets:
            self.targets.append(target)
            self.transceiver = self.transceiver_factory(self.sources, self.send, self.targets)

    def receive(self, payload: Any) -> Any:
        return self.transceiver(payload)

    def send(self, target: GenericComponent, payload: Any) -> Any:
        return target.receive(payload)


class TestConfig:
    '''A possible interface for inferring and representing a directed graph.

    Presently only used to link components using the `add_source()` and `add_target()` methods.
    '''
    def add_edge(self, source: GenericComponent, target: GenericComponent) -> 'TestConfig':
        '''Add a single directed edge to the graph.
        '''
        target.add_source(source)
        source.add_target(target)
        return self

    def add_edges(self, *edges: Tuple[GenericComponent, GenericComponent]) -> 'TestConfig':
        '''Add a bunch of directed edges to the graph, given as 2-tuples.
        '''
        for edge in edges:
            source, target = edge
            self.add_edge(source, target)
        return self


class MockHttpMessage(BaseModel):
    '''An abstraction/mock of the Flask Request Object.
    '''
    content_type: str = Field('text/plain')
    data: bytes = Field(b'')
    headers: Mapping[str, str] = Field(default_factory=dict)

    def get_data(self) -> bytes:
        '''Mocks the `Request.get_data()` method.
        '''
        return self.data

    def get_json(self) -> Optional[Any]:
        '''Mocks the `Request.get_json()` method.
        '''
        if self.content_type == 'application/json':
            return json.loads(self.data)
        return None


class MockFlowMessages(BaseModel):
    '''A factory for constructing dummy REXFlow messages.
    '''
    flow_id: str = '0123456789'

    def obj_to_json(self, obj):
        headers = {Headers.X_HEADER_FLOW_ID: self.flow_id}
        return MockHttpMessage(
            content_type='application/json',
            data=json.dumps(obj).encode(),
            headers=headers
        )
