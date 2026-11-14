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
