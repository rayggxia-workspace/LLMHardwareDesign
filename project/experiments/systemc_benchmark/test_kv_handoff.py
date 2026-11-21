import sys
from pathlib import Path
import unittest

import numpy as np

FROZEN = Path(__file__).resolve().parents[3] / 'work/YUZE-LU/234/raw/frozen220/project/experiments/block_synthesis'


@unittest.skipUnless(FROZEN.is_dir(), 'requires pinned old220 numerical fixture')
class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(FROZEN))
        from full_integer import Q
        from kv_handoff import handoff
        cls.Q, cls.transfer = Q, staticmethod(handoff)

    def inputs(self):
        outputs, formats = {}, {}
        for i in range(2):
            for k in ('k', 'v'):
                raw = np.array([100000, -200000, 300000, -400000], dtype=np.int64)
                outputs['next_%d_%s' % (i, k)] = self.Q(raw.reshape(1, 1, 2, 2), -20)
                formats['past_%d_%s' % (i, k)] = {'shape': [1, 1, 2, 2], 'bits': 32,
                                               'exponent': -20}
        return outputs, {'runtime_formats': formats,
                         'initial_formats': {n: dict(m, runtime=True) for n, m in formats.items()}}

    def test_all_layers_bits_and_owned_arrays(self):
        outputs, program = self.inputs()
        states, audit = self.transfer(outputs, program, 2)
        self.assertEqual(audit['state_count'], 4)
        self.assertEqual(audit['prefix_tokens'], 2)
        for n, q in states.items():
            expected = outputs[n.replace('past_', 'next_')]
            np.testing.assert_array_equal(q.raw, expected.raw)
            self.assertEqual(q.exponent, expected.exponent)
            self.assertFalse(np.shares_memory(q.raw, expected.raw))

    def test_missing_hf_float_or_partial_state_rejected(self):
        outputs, program = self.inputs()
        for bad in (None, np.ones((1, 1, 2, 2), np.float32)):
            outputs['next_0_k'] = bad
            with self.assertRaises(ValueError):
                self.transfer(outputs, program, 2)
        outputs, program = self.inputs()
        del program['runtime_formats']['past_1_v']
        with self.assertRaises(ValueError):
            self.transfer(outputs, program, 2)

    def test_scale_length_and_range_changes_rejected(self):
        for field, value in (('exponent', -19), ('shape', [1, 1, 3, 2]), ('bits', 16)):
            outputs, program = self.inputs()
            for d in (program['runtime_formats'], program['initial_formats']):
                d['past_0_k'][field] = value
            with self.assertRaises(ValueError):
                self.transfer(outputs, program, 2)
        outputs, program = self.inputs()
        outputs['next_0_k'].raw[:] = 1 << 32
        with self.assertRaises(ValueError):
            self.transfer(outputs, program, 2)


if __name__ == '__main__':
    unittest.main()
