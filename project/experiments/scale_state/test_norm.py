from fractions import Fraction
import math
import unittest
import numpy as np
from norm import compile_constants, divide64, encode16, encode8, integer_norm, sqrt32


class IntegerNorm(unittest.TestCase):
    def test_isqrt_restoring_64bit_boundaries(self):
        for n in [0, 1, 2, 3, 4, 15, 16, 17, (1 << 32)-1, 1 << 32, (1 << 64)-1]:
            self.assertEqual(sqrt32(n), math.isqrt(n))
        with self.assertRaises(OverflowError): sqrt32(1 << 64)

    def test_unsigned_restoring_divider_ties_and_ranges(self):
        for n in [0, 1, 3, 5, 7, 1 << 45, (1 << 64)-1]:
            for d in [1, 2, 3, 16, (1 << 32)-1]:
                self.assertEqual(divide64(n, d), round(Fraction(n, d)))
        for d in [0, -1, 1 << 32]:
            with self.assertRaises(ValueError): divide64(1, d)

    def test_dynamic16_negative_shift_and_mixed_units(self):
        sums = np.array([[1, -2, 0, 0], [127, -127, 1, 2]], dtype=np.int64)
        units = np.array([[-20, -21, -20, -20], [-10, -11, -10, -10]], dtype=np.int16)
        x, e = encode16(sums, units)
        for row in range(2):
            self.assertGreaterEqual(int(np.max(abs(x[row].astype(np.int32)))), 16384)
            for col in range(4):
                self.assertEqual(int(x[row, col]), round(Fraction(int(sums[row, col]))*Fraction(2)**(int(units[row, col])-int(e[row]))))

    def test_integer_norm_zero_epsilon_and_gamma(self):
        H = 128; gamma, eps, sqrtH = compile_constants(np.zeros(H, dtype=np.float32), H)
        sums = np.ones((2, H), dtype=np.int64)*1048576; sums[0] = 0
        units = np.full(sums.shape, -20, dtype=np.int16)
        result = integer_norm(sums, units, gamma, eps, sqrtH)
        self.assertFalse(result['norm_S32Q20'][0].any())
        self.assertTrue(np.all(abs(result['norm_S32Q20'][1].astype(np.float64)/1048576-1) < 2e-5))
        gamma2, _, _ = compile_constants(np.ones(H, dtype=np.float32), H)
        doubled = integer_norm(sums, units, gamma2, eps, sqrtH)
        self.assertTrue(np.array_equal(doubled['norm_S32Q20'], result['norm_S32Q20']*2))

    def test_integer_fresh_a8_no_float_bridge_and_failure_domains(self):
        source = np.tile(np.array([-2147483648, -7, -3, -1, 0, 1, 3, 7], dtype=np.int32), 16)[None]
        a, e = encode8(source)
        for j in range(128): self.assertEqual(int(a[0, j]), round(Fraction(int(source[0, j]))*Fraction(2)**(-20-int(e[0, 0]))))
        with self.assertRaises(ValueError): encode8(source[:, :127])
        gamma, eps, sqrtH = compile_constants(np.zeros(128, dtype=np.float32), 128)
        with self.assertRaises(OverflowError): integer_norm(np.ones((1, 128), dtype=np.int64), np.full((1, 128), -60, dtype=np.int16), gamma, eps, sqrtH)
        with self.assertRaises(OverflowError): encode16(np.array([[1 << 62, 1]], dtype=np.int64), np.array([[0, -2]], dtype=np.int16))
        with self.assertRaises(OverflowError): compile_constants(np.full(128, 3000, dtype=np.float32), 128)


if __name__ == '__main__': unittest.main()
