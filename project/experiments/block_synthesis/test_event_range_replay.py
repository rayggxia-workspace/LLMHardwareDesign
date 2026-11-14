"""Check the range ACK boundary against the integer control interpreter."""
import unittest

import numpy as np

from event_range_replay import replay_ranges
from full_integer import Q


class RangeReplayTest(unittest.TestCase):
    def test_consumer_reads_committed_rows(self):
        def convert(name, kernel, source):
            return {'id': name, 'kernel': kernel, 'op': 'Convert', 'inputs': [source],
                    'shape': [2, 2], 'exponent': 0, 'bits': 32, 'attributes': {'shift': 0}}

        def descriptor(kernel, name, row):
            return {'kernel': kernel, 'rows': [row, row + 1],
                    'output_indices': {name: [2 * row, 2 * row + 2]}}

        program = {'instructions': [convert('x', 'produce', 'input'), convert('y', 'consume', 'x')],
                   'predicates': {}, 'outputs': {'output': 'y'}}
        value = np.array([[1, 2], [3, 4]], dtype=np.int64)
        first = ('produce0', descriptor('produce', 'x', 0))
        second = ('produce1', descriptor('produce', 'x', 1))
        consume_first = ('consume0', descriptor('consume', 'y', 0))
        consume_second = ('consume1', descriptor('consume', 'y', 1))
        initial = {'input': Q(value, 0)}
        result = replay_ranges(program, [first, consume_first, second, consume_second], initial, [[]], None)
        np.testing.assert_array_equal(result['output'].raw, value)
        with self.assertRaisesRegex(ValueError, 'uncommitted range'):
            replay_ranges(program, [first, consume_second, second, consume_first], initial, [[]], None)

    def test_feature_tiles_keep_full_dot_and_feed_only_committed_columns(self):
        dot = {'id': 'x', 'kernel': 'dot', 'op': 'Dot', 'inputs': ['a', 'b'],
               'shape': [1, 3], 'exponent': 1, 'bits': 32,
               'attributes': {'shift': 1, 'length': 2}}
        add = {'id': 'y', 'kernel': 'add', 'op': 'Add', 'inputs': ['x', 'bias'],
               'shape': [1, 3], 'exponent': 1, 'bits': 32,
               'attributes': {'signs': [1, 1]}}
        program = {'instructions': [dot, add], 'predicates': {}, 'outputs': {'result': 'y'}}
        initial = {'a': Q(np.array([[2, 3]]), 0),
                   'b': Q(np.array([[1, 2, 3], [3, 2, 1]]), 0),
                   'bias': Q(np.array([10, 20, 30]), 1)}

        def range_command(node, first, stop):
            return f"{node['kernel']}{first}", {
                'kernel': node['kernel'], 'rows': [0, 1], 'columns': [first, stop],
                'output_indices': {node['id']: [first, stop]}}

        first = [range_command(node, 0, 2) for node in (dot, add)]
        tail = [range_command(node, 2, 3) for node in (dot, add)]
        result = replay_ranges(program, first + tail, initial, [[]], None)
        np.testing.assert_array_equal(result['result'].raw, [[16, 25, 34]])
        with self.assertRaisesRegex(ValueError, 'uncommitted range'):
            replay_ranges(program, [first[0], tail[1], tail[0], first[1]], initial, [[]], None)
