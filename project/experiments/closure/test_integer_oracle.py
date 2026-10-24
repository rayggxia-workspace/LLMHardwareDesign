"""Scalar boundary tests; these do not execute models or claim runtime speed."""
import math
import random
import unittest
from fractions import Fraction

import integer_oracle as oracle


class OracleTests(unittest.TestCase):
    def test_ties_positive_negative_and_cancellation(self):
        expected = {-7: -4, -5: -2, -3: -2, -1: 0, 1: 0, 3: 2, 5: 2, 7: 4}
        for n, answer in expected.items():
            self.assertEqual(oracle.round_rational(n, 2), answer)
        for n in range(-91, 92):
            for d in range(1, 26):
                self.assertEqual(oracle.round_rational(n, d), round(Fraction(n, d)))

    def test_saturation_edges(self):
        for width in (8, 16, 32, 64):
            lo, hi = oracle.signed_limits(width)
            self.assertEqual(oracle.saturate(lo, width), (lo, False))
            self.assertEqual(oracle.saturate(hi, width), (hi, False))
            self.assertEqual(oracle.saturate(lo - 1, width), (lo, True))
            self.assertEqual(oracle.saturate(hi + 1, width), (hi, True))

    def test_mul_requant_not_preclipped(self):
        self.assertEqual(oracle.requant(127, 3, 1, 8),
                         dict(product=381, rounded=190, code=127, saturated=True))
        self.assertEqual(oracle.requant(-127, 3, 1, 8)["rounded"], -190)
        self.assertEqual(oracle.shift_rne(-3, -2), -12)

    def test_complete_dot_checks_prefix_overflow(self):
        self.assertEqual(oracle.complete_dot([127, -127], [127, 127]), 0)
        with self.assertRaisesRegex(ValueError, "overflow"):
            oracle.complete_dot([127] * 3 + [-127] * 3, [127] * 6, 16)

    def test_s8_lowering_all_signs_minima_fixed_count(self):
        for bits in (8, 16, 32, 64):
            lo, hi = oracle.signed_limits(bits)
            for a in (lo, -1, 0, 1, hi):
                for b in (-32768, -1, 0, 1, 32767):
                    r = oracle.lowered_product(a, b, bits, 16)
                    self.assertEqual(r["value"], a * b)
                    count = 1 if bits == 8 else 1 + (bits - 8 + 6) // 7
                    self.assertEqual(r["s8_products"], count * 3)
                    self.assertEqual(r["wide_shift_adds"], r["s8_products"])

    def test_restoring_division_and_nearest_even(self):
        for n in range(513):
            for d in range(1, 38):
                self.assertEqual(oracle.unsigned_divmod_bits(n, d, 16), divmod(n, d))
                self.assertEqual(oracle.divided_rne(n, d, 16), round(Fraction(n, d)))
                self.assertEqual(oracle.divided_rne(-n, d, 16), round(Fraction(-n, d)))
        n = (1 << 127) - 1
        self.assertEqual(oracle.divided_rne(n, 7, 128), round(Fraction(n, 7)))

    def test_restoring_sqrt_square_neighbours_and_full_width(self):
        samples = list(range(1500))
        for square in (127 ** 2, 65535 ** 2, ((1 << 63) - 1) ** 2):
            samples.extend((square - 1, square, square + 1))
        for n in samples:
            self.assertEqual(oracle.isqrt_bits(n, 128), math.isqrt(n))
        self.assertEqual(oracle.isqrt_bits((1 << 128) - 1, 128), (1 << 64) - 1)

    def test_lut_edges_and_stable_exact_ties(self):
        self.assertEqual(oracle.lookup([3, 5, 9], -8), 3)
        self.assertEqual(oracle.lookup([3, 5, 9], 9), 9)
        with self.assertRaisesRegex(ValueError, "out of range"):
            oracle.lookup([3], 1, "reject")
        self.assertEqual(oracle.stable_topk([4, 4, 2, 5], 3), [3, 0, 1])

    def test_reject_silent_float_bool_unbounded_and_div_zero(self):
        for bad in (1.0, True):
            with self.assertRaises(ValueError):
                oracle.shift_rne(bad, 1)
        for fn, args in ((oracle.shift_rne, (1, 257)),
                         (oracle.divided_rne, (3, 0)),
                         (oracle.isqrt_bits, (-1,)),
                         (oracle.lookup, ([1.0], 0))):
            with self.assertRaises(ValueError):
                fn(*args)


if __name__ == "__main__":
    unittest.main()
