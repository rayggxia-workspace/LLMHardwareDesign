"""Small independent arithmetic/transaction boundary tests, no model loading."""
import importlib.util
from fractions import Fraction
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location("independent_range", Path(__file__).with_name("receive_range.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RangeAuditTests(unittest.TestCase):
    def test_signed_nearest_even(self):
        for shift in range(-3, 18):
            for n in (-(1 << 63), -65535, -9, -5, -3, -1, 0, 1, 3, 5, 9, 65535, (1 << 63) - 1):
                self.assertEqual(r.rne(n, shift), round(Fraction(n) * Fraction(2) ** -shift))

    def test_same_physical_bounds(self):
        lo, hi = r.bounds(32)
        self.assertEqual((lo, hi), (-32768 << 16, 32767 << 16))
        self.assertLess(hi, (1 << 31) - 1)

    def test_current_proposal_guard(self):
        a = np.array([[[32767]]], np.int64)
        q = k = v = np.array([[32767]], np.int64)
        proposal, clipped, out, guard, _ = r.oracle_step(a, q, k, v, [32768], [32768], [0], [0], 16, 15)
        self.assertEqual(int(proposal[0, 0, 0]), 32768)
        self.assertEqual(int(clipped[0, 0, 0]), 32767)
        self.assertEqual(guard, [1])
        self.assertEqual(int(out[0, 0]), 32766)
        self.assertEqual(int(a[0, 0, 0]), 32767)

    def test_retry_recomputes_whole_token(self):
        a = np.array([[[32767]]], np.int64)
        q = k = v = np.array([[32767]], np.int64)
        s, u = r.rescale(a, [0], [1])
        proposal, _, _, guard, _ = r.oracle_step(s, q, k, v, [32768], [32768], u, [0], 16, 15)
        self.assertEqual((int(s[0, 0, 0]), int(u[0])), (16384, 1))
        self.assertEqual(guard, [0])
        self.assertEqual(int(proposal[0, 0, 0]), 16384)

    def test_repeated_rne_cannot_collapse(self):
        a, u = np.array([[[5]]], np.int64), np.array([0], np.int16)
        for _ in range(3):
            a, u = r.rescale(a, u, [1])
        self.assertEqual(int(a[0, 0, 0]), 0)
        self.assertEqual(r.rne(5, 3), 1)
        self.assertEqual(int(u[0]), 3)

    def test_only_bad_heads_recode(self):
        a = np.array([[[5]], [[7]]], np.int64)
        got, units = r.rescale(a, [-2, -3], [0, 1])
        np.testing.assert_array_equal(got, [[[5]], [[4]]])
        np.testing.assert_array_equal(units, [-2, -2])

    def test_epoch_unit_overflow_rejects(self):
        with self.assertRaisesRegex(AssertionError, "unit rescale domain"):
            r.rescale(np.array([[[1]]]), [127], [1])

    def test_gate_domain_and_state_shape(self):
        a = np.zeros((1, 1, 1), np.int64)
        q = np.zeros((1, 1), np.int64)
        with self.assertRaisesRegex(AssertionError, "operand domain decay"):
            r.oracle_step(a, q, q, q, [32769], [0], [0], [0], 16, 15)


if __name__ == "__main__":
    unittest.main()
