"""Meaningful independent arithmetic, width, negative-control and resource checks."""
from collections import Counter
from fractions import Fraction
import random
import unittest
import json
from pathlib import Path

from core import requant_wide, align_pv, pv_block, integer_attention
from oracle import attention
from run import transport, bias_experiment
from tables import load


class TestIntegerBoundary(unittest.TestCase):
    def test_rq33_independent_boundary_and_random(self):
        rng = random.Random(39)
        values = [-2**32, -2**31, -5, -3, -1, 0, 1, 3, 5, 2**31-1, 2**32-2]
        values += [rng.randrange(-2**32, 2**32) for _ in range(200)]
        for value in values:
            for m, r in ((1, 1), (2**31-1, 31), (1234567, 45), (0, 0), (1, 63)):
                expected = max(-32768, min(32767, round(Fraction(value*m, 2**r))))
                self.assertEqual(requant_wide(value, m, r, 16, 33, Counter()), expected)
        with self.assertRaises(OverflowError):
            requant_wide(2**32, 1, 0, 8, 33, Counter())

    def test_align_before_final_round(self):
        # Two half-unit partials: rounding each first loses both; late RNE gives one.
        result, _, _ = align_pv([[1], [1]], [-13, -13], 7, Counter())
        self.assertEqual(result, [0])  # actual P denominator is127, not128
        result, _, _ = align_pv([[127], [127]], [-13, -13], 7, Counter())
        self.assertEqual(result, [1])
        wrong = round(Fraction(127, 254)) + round(Fraction(127, 254))
        self.assertEqual(wrong, 0)

    def test_variable_scale_signed_fraction(self):
        rng = random.Random(3901)
        for _ in range(100):
            partials = [[rng.randrange(-100000, 100000) for _ in range(8)] for _ in range(4)]
            exps = [-14, -9, -7, -12]
            got, _, _ = align_pv(partials, exps, 15, Counter())
            expected = [max(-32768, min(32767, round(sum(Fraction(partials[i][d], 32767)
                       * Fraction(1, 2**-exps[i]) for i in range(4))*4096))) for d in range(8)]
            self.assertEqual(got, expected)

    def test_wrong_V_scale_is_detectable(self):
        got, _, _ = align_pv([[127], [127]], [-12, -9], 7, Counter())
        self.assertEqual(got, [9])
        wrong, _, _ = align_pv([[127], [127]], [-12, -12], 7, Counter())
        self.assertEqual(wrong, [2])
        self.assertNotEqual(got, wrong)

    def test_P7_long_uniform_zero_and_P15_cost(self):
        from vectors import softmax_fixed
        table = load()["exp_u32_f24"]
        p7, _ = softmax_fixed([0]*512, table, 7)
        p15, _ = softmax_fixed([0]*512, table, 15)
        self.assertEqual(sum(p7), 0)
        self.assertGreater(sum(p15), 0)

    def test_mutable_block_scale_changes_old_tokens(self):
        import numpy as np
        from run import quantize
        before, eb, _ = quantize(np.array([[1.0, 0.5]]))
        after, ea, _ = quantize(np.array([[1.0, 0.5], [1024.0, 0.0]]))
        self.assertNotEqual(eb, ea)
        self.assertFalse(np.array_equal(before[0], after[0]))

    def test_reject_silent_wide_overflow(self):
        with self.assertRaises(OverflowError):
            align_pv([[2**31-1], [2**31-1]], [-1, 31], 15, Counter())
        with self.assertRaises(OverflowError):
            pv_block([32767]*513, [[127]]*513, Counter())
        with self.assertRaises(OverflowError):
            align_pv([[2**31-1], [2**31-1]], [30, 30], 15, Counter())

    def test_pv_16x8_exact_and_cost(self):
        counts = Counter()
        self.assertEqual(pv_block([32767, 1], [[-128, 127], [127, -128]], counts),
                         [-32767*128+127, 32767*127-128])
        self.assertEqual(counts["mul8_partial_products"], 12)
        counts = Counter()
        self.assertEqual(pv_block([127], [[-128, 127]], counts, 7), [-16256, 16129])
        self.assertEqual(counts["mul8_partial_products"], 2)

    def test_full_attention_oracle_and_mask(self):
        table = load()["exp_u32_f24"]
        q, k, v = [[1, -2], [3, 4]], [[2, -1], [4, 1]], [[127, -128], [-127, 127]]
        mask, params = [[True, False], [True, True]], [[(1, 0), (2, 0)]]*2
        rows, _ = integer_attention(q, k, v, [-4, -3], [-8, -5], params, 1, 15, mask, table)
        oracle = attention(q, k, v, [-8, -5], params, 1, 15, mask, table)
        for row, ref in zip(rows, oracle):
            for key, value in ref.items():
                self.assertEqual(row[key], value)
        self.assertEqual(rows[0]["probabilities"][1], 0)
        with self.assertRaises(ValueError):
            integer_attention(q, k, v, [-4, -3], [-8, -5], params, 1, 15,
                              [[False, False], [True, True]], table)

    def test_bias_i32_wrapping_and_row_scale_detected(self):
        report = bias_experiment()
        self.assertTrue(all(r["wrap_detected"] for r in report["boundary"][:2]))
        self.assertTrue(all(r["detected"] for r in report["dynamic_scale"][1:]))

    def test_boundary_inventory_and_padding(self):
        cfg = json.loads(Path(__file__).with_name("experiment.json").read_text())
        records = transport(cfg)
        self.assertEqual(len(records), 12)
        single = records[0]
        self.assertEqual(single["near_reducer_physical_bytes"], 320)
        self.assertEqual(single["shared_reducer_physical_bytes"], 576)
        self.assertEqual(records[3]["shared_reducer_physical_bytes"], 4608)
        self.assertTrue(all(r["max_packet_bytes"] <= 2048 for r in records))
        self.assertEqual(sum(records[-1]["row_microtiles"]), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
