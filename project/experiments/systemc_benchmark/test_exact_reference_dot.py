import unittest
import numpy as np
from exact_reference_dot import ExactReferenceDot


class ExactDotTests(unittest.TestCase):
    def check(self, x, y):
        engine = ExactReferenceDot()
        result = engine.dot({}, x, y)
        # Python arbitrary precision, independent of BLAS/NumPy integer overflow.
        expected = np.matmul(x.astype(object), y.astype(object))
        np.testing.assert_array_equal(result, expected)
        return engine.calls

    def test_small_and_large_signed_batched_products(self):
        rng = np.random.default_rng(234)
        for scale in (127, 32767, (1 << 25) - 1):
            x = rng.integers(-scale, scale, (2, 3, 128), dtype=np.int64)
            y = rng.integers(-scale, scale, (1, 128, 5), dtype=np.int64)
            counts = self.check(x, y)
        self.assertEqual(counts['radix16_binary64_proven'], 1)

    def test_negative_radix_boundaries_and_cancellation(self):
        x = np.array([[-65537, -65536, -1, 0, 65535, 65536, 65537]], dtype=np.int64)
        y = (x.T * (1 << 12)).astype(np.int64)
        self.check(x, y)

    def test_s64_overflow_rejected(self):
        x = np.full((1, 8), (1 << 31) - 1, dtype=np.int64)
        with self.assertRaises(ValueError):
            ExactReferenceDot().dot({}, x, x.T)

    def test_safe_integer_fallback_near_s64_limit(self):
        x = np.full((1, 2), -(1 << 31) + 1, dtype=np.int64)
        counts = self.check(x, x.T)
        self.assertEqual(counts['integer_fallback'], 1)


if __name__ == '__main__':
    unittest.main()
