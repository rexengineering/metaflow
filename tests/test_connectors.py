#!python3
'''Unit tests for flowlib.connectors.'''
from typing import Any, Iterable, Optional
import unittest
from uuid import uuid4

from flowlib import connectors, constants, stores
from .harness import (
    GenericComponent,
    GenericDownstream,
    GenericUpstream,
    MockFlowMessages,
    ReceiverType,
    TestComponent,
    TestConfig,
    TransceiverFactoryType,
    TransmitterType,
)


def make_parallel_connector_factory(
    merge_mode = constants.Parallel.MergeModes.OBJECT,
    store_opt: Optional[stores.KVStore[Any]] = None,
) -> TransceiverFactoryType:
    '''Creates a concrete parallel connector test harness factory.

    Note that the transceiver does not fully model the intended behavior of the
    Connector interface since `handle_data()` is not called in a separate thread
    of execution.  Instead, it makes blocking downstream transmissions
    immediately following input validation.
    '''
    def parallel_connector_factory(
        sources: Iterable[GenericComponent],
        transmitter: TransmitterType,
        targets: Iterable[GenericComponent]
    ) -> ReceiverType:
        '''Factory function for creating a ParallelConnector using test harness I/O.
        '''
        in_edges = [
            connectors.Connection(str(obj_no), f'https://upstream_{obj_no}/', {})
            for obj_no, _ in enumerate(sources)
        ]
        # TODO: Consider making the HTTP method configurable.
        out_edges = [
            connectors.Connection(str(obj_no), f'https://downstream_{obj_no}/', {'method': 'post'})
            for obj_no, _ in enumerate(targets)
        ]
        downstream_map = {
            out_edge.k8s_url : target
            for out_edge, target in zip(out_edges, targets)
        }

        def send_downstream(target_addr, target_payload) -> None:
            '''Closure for sending a payload to the given target address.
            '''
            assert transmitter(downstream_map[target_addr], target_payload)

        connector = connectors.ParallelConnector(
            str(uuid4()),
            in_edges,
            out_edges,
            {'post': send_downstream},
            merge_mode,
            stores.InMemoryStore() if store_opt is None else store_opt
        )

        def receiver(upstream_payload) -> Any:
            '''Closure for mocking the reception of a HTTP request.
            '''
            if connector.is_valid(upstream_payload):
                connector.handle_data(upstream_payload)
                return True
            return False

        return receiver

    return parallel_connector_factory


def build_test_components(source_count: int, target_count: int, *args, **kws):
    '''Creates the unit test harness objects given a configuration.
    '''
    sources = [GenericUpstream() for _ in range(source_count)]
    targets = [GenericDownstream() for _ in range(target_count)]
    factory = make_parallel_connector_factory(*args, **kws)
    return sources, TestComponent(factory, sources, targets), targets


class TestConnectors(unittest.TestCase):
    '''Unit test cases for the flowlib.connectors module.
    '''
    def test_one_to_many(self):
        '''Tests a one to many parallel connector.
        '''
        message_factory = MockFlowMessages()
        sources, unit, targets = build_test_components(1, 3)
        source = sources[0]
        TestConfig().add_edge(source, unit).add_edges(*((unit, target) for target in targets))
        self.assertTrue(all(len(target.received) == 0 for target in targets))
        source.receive(message_factory.obj_to_json(42))
        self.assertTrue(all(len(target.received) == 1 for target in targets))
        source.receive(message_factory.obj_to_json(99))
        self.assertTrue(all(len(target.received) == 2 for target in targets))

    def _test_many_to_one(self, merge_mode: constants.Parallel.MergeModes):
        '''Configurable utility for testing a many to one parallel connector.
        '''
        message_factory = MockFlowMessages()
        sources, unit, targets = build_test_components(3, 1, merge_mode)
        target = targets[0]
        TestConfig().add_edges(*((source, unit) for source in sources)).add_edge(unit, target)
        for round_no in range(4):
            self.assertEqual(len(target.received), round_no)
            sources[0].receive(message_factory.obj_to_json({'A': 1}))
            self.assertEqual(len(target.received), round_no)
            sources[1].receive(message_factory.obj_to_json({'B': 1}))
            self.assertEqual(len(target.received), round_no)
            sources[2].receive(message_factory.obj_to_json({'A': 1}))
            self.assertEqual(len(target.received), round_no + 1)
        return sources, unit, targets

    def test_many_to_one_array(self):
        '''Tests a many to one parallel connector configured to merge incoming data as arrays.
        '''
        _, _, targets = self._test_many_to_one(constants.Parallel.MergeModes.ARRAY)
        result = targets[0].received[0]
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

    def test_many_to_one_object(self):
        '''Tests a many to one parallel connector configured to merge incoming data as object
        attributes.
        '''
        _, _, targets = self._test_many_to_one(constants.Parallel.MergeModes.OBJECT)
        result = targets[0].received[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)

    def test_many_to_one_update(self):
        '''Tests a many to one parallel connector configured to merge incoming data as a unified
        object.
        '''
        _, _, targets = self._test_many_to_one(constants.Parallel.MergeModes.UPDATE)
        result = targets[0].received[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)

    def _test_store_noninterference(self, merge_mode: constants.Parallel.MergeModes):
        '''Configurable utility for testing a many to one parallel connector with multiple flow instances.
        '''
        concurrency = 3
        message_factories = [MockFlowMessages(flow_id=str(iid)) for iid in range(concurrency)]
        sources, unit, targets = build_test_components(3, 1, merge_mode)
        target = targets[0]
        TestConfig().add_edges(*((source, unit) for source in sources)).add_edge(unit, target)
        expected_len = 0
        for round_no in range(4):
            self.assertEqual(expected_len, round_no * concurrency)
            self.assertEqual(len(target.received), expected_len)
            for source in sources[:-1]:
                for iid in range(concurrency):
                    source.receive(message_factories[iid].obj_to_json({'ABC'[iid]: round_no}))
                    self.assertEqual(len(target.received), expected_len)
            source = sources[-1]
            for iid in range(concurrency):
                source.receive(message_factories[iid].obj_to_json({'ABC'[iid]: round_no}))
                expected_len += 1
                self.assertEqual(len(target.received), expected_len)
        return sources, unit, targets

    def test_store_noninterference(self):
        _, _, targets = self._test_store_noninterference(constants.Parallel.MergeModes.ARRAY)
        result = targets[0].received
        self.assertIsInstance(result[0], list)
        self.assertEqual(len(result[0]), 3)


if __name__ == '__main__':
    unittest.main()
