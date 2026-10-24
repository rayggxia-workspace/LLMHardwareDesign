import copy
from fractions import Fraction
import unittest
from unittest.mock import patch
import numpy as np
import receive_state_extra as e


class ExtraReceiverTests(unittest.TestCase):
    def test_cover_boundary_and_floor(self):
        self.assertEqual(e.cover([32767 / 16], 32767), -4)
        self.assertEqual(e.cover([0], 32767, headroom=2, floor=-26, zero=-20), -20)
        self.assertEqual(e.cover([1e-15], 32767, headroom=2, floor=-26), -26)
        for maximum in (2**-30, 1 / 3, 8, 32767 / 16):
            unit = e.cover([maximum], 127)
            self.assertGreaterEqual(Fraction(127) * Fraction(2)**unit, Fraction(maximum))
            self.assertLess(Fraction(127) * Fraction(2)**(unit - 1), Fraction(maximum))

    def test_unsigned_endpoint_and_fraction_ties(self):
        source = dict(q=np.zeros((32, 2, 128)), k=np.zeros((32, 2, 128)),
                      v=np.zeros((32, 2, 128)), beta=np.ones((32, 2)), g=np.zeros((32, 2)))
        codes, clips = e.encode_source(source, [-10, -10], 31)
        self.assertTrue(np.all(codes['decay'] == 2**31))
        self.assertTrue(np.all(codes['beta'] == 32768))
        self.assertEqual(clips, dict(q=0, k=0, v=0, beta=0, decay=0))
        q, clips = e.fraction_encode([.5, 1.5, 2.5, -.5, -1.5, -2.5], 0, -2, 2)
        np.testing.assert_array_equal(q, [0, 2, 2, 0, -2, -2])
        self.assertEqual(clips, 0)

    def test_normalization_uses_l2_and_complete_K(self):
        payload = dict(query=np.ones((1, 32, 2, 128)), key=np.ones((1, 32, 2, 128)),
                       value=np.zeros((1, 32, 2, 128)), beta=np.zeros((1, 32, 2)), g=np.zeros((1, 32, 2)))
        got = e.normalized(payload)
        self.assertAlmostEqual(got['q'][0, 0, 0], 1 / np.sqrt(128 + 1e-6) / np.sqrt(128), places=15)
        self.assertAlmostEqual(got['k'][0, 0, 0], 1 / np.sqrt(128 + 1e-6), places=15)

    def test_eight_chunks_carry_computed_state(self):
        T = 256
        arrays = {k: np.zeros((T, 2, 128), np.int16) for k in ('q', 'k', 'v')}
        arrays.update(beta=np.zeros((T, 2), np.uint16), decay=np.zeros((T, 2), np.uint32),
                      state_initial=np.zeros((2, 128, 128), np.int16),
                      state_trace=np.broadcast_to(np.arange(T + 1)[:, None, None, None], (T + 1, 2, 128, 128)),
                      output_codes=np.zeros((T, 2, 128), np.int64))
        calls = []
        def fake(q, k, v, beta, decay, initial, ev, es, lo, hi, wanted_output, wanted_states, decay_fraction):
            start = len(calls) * 32
            self.assertTrue(np.all(initial == start))
            np.testing.assert_array_equal(initial, wanted_states[0])
            calls.append(start)
            s = initial[None] + np.arange(33)[:, None, None, None]
            return wanted_output.copy(), s, {'steps': 32}, {'stage': start + 32}, {'stage': 10}
        with patch.object(e.b, 'integer_oracle', fake):
            y, s, counts, maxima, _ = e.continuous_oracle(arrays, [-10, -10], [-12, -12], -32768, 32767, 31)
        self.assertEqual(calls, list(range(0, 256, 32)))
        self.assertEqual(s.shape, (257, 2, 128, 128))
        self.assertTrue(np.all(s[-1] == 256))
        self.assertEqual(counts, {'steps': 256})
        self.assertEqual(maxima, {'stage': 256})

    def test_actual_integer_oracle_full32_and_unsigned_exact1(self):
        T = 32
        arrays = {k: np.zeros((T, 2, 128), np.int16) for k in ('q', 'k', 'v')}
        arrays.update(beta=np.full((T, 2), 32768, np.uint16), decay=np.full((T, 2), 2**31, np.uint32),
                      state_initial=np.zeros((2, 128, 128), np.int32),
                      state_trace=np.zeros((T + 1, 2, 128, 128), np.int32),
                      output_codes=np.zeros((T, 2, 128), np.int64))
        y, s, counts, _, _ = e.continuous_oracle(arrays, [-10, -10], [-28, -28], -(1 << 31), 32767 << 16, 31)
        self.assertEqual(counts['state_saturations'], 0)
        self.assertEqual(counts['output_Fraction_RNE'], 32 * 2 * 128)
        self.assertFalse(np.any(y))
        self.assertFalse(np.any(s))
        arrays['output_codes'][0, 0, 0] = 1
        with self.assertRaisesRegex(AssertionError, 'integer output oracle'):
            e.continuous_oracle(arrays, [-10, -10], [-28, -28], -(1 << 31), 32767 << 16, 31)

    def test_actual256_commit_boundary_rejects_old_state(self):
        states = np.zeros((257, 2, 1, 1), np.int64)
        outputs = np.zeros((256, 2, 1), np.int64)
        fmt = dict(window='layer14-end8192', sequence='unknown:layer14-end8192: no cross-window commits',
                   head_slots=[0, 1], format_epoch=0)
        contract = e.b.json_digest(fmt)
        events = [dict(version=t+1, position=7937+t, contract=contract,
                       old_state_sha256=e.b.semantic_digest(states[t]),
                       state_sha256=e.b.semantic_digest(states[t+1]),
                       output_sha256=e.b.semantic_digest(outputs[t])) for t in range(256)]
        row = dict(format=fmt, execution=dict(commits=events, final_version=256, final_position=8192))
        e.commits(row, states, outputs, 'source', 7936, legacy=True)
        bad = copy.deepcopy(row)
        bad['execution']['commits'][32]['old_state_sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'integer commit continuity 32'):
            e.commits(bad, states, outputs, 'source', 7936, legacy=True)


if __name__ == '__main__':
    unittest.main()
