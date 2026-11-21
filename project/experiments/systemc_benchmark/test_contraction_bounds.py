"""Independent arbitrary-precision checks for long/sparse accumulator proofs."""
import unittest
import numpy as np
from contraction_bounds import absolute_contraction_bound
from exact_reference_dot import ExactReferenceDot


class ContractionProof(unittest.TestCase):
    def test_long_probability_sum_does_not_require_max_times_length(self):
        # Native max*max*K exceeds S64, but only one probability is nonzero.
        x = np.zeros((1, 2049), dtype=np.int64)
        x[0, 0] = 1 << 30
        y = np.full((2049, 2), 1 << 24, dtype=np.int64)
        self.assertGreater((int(x.max())+131072)*(int(y.max())+131072)*2049, (1 << 63)-1)
        self.assertLess(absolute_contraction_bound(x, y, decomposed=True), (1 << 63)-1)
        actual = ExactReferenceDot().dot({}, x, y)
        self.assertEqual(actual.tolist(), [[1 << 54, 1 << 54]])

    def test_bound_covers_every_signed_component_product(self):
        rng = np.random.default_rng(234)
        def norm(v):
            low = (v+32768) % 65536-32768
            high = v >> 16
            return abs(low)+65536*abs(high)+65536*(low < 0)
        for _ in range(25):
            x = rng.integers(-(1 << 31), 1 << 31, (3, 7), dtype=np.int64)
            y = rng.integers(-(1 << 31), 1 << 31, (7, 4), dtype=np.int64)
            ordinary = max(sum(abs(int(x[i,k])*int(y[k,j])) for k in range(7))
                           for i in range(3) for j in range(4))
            component = max(sum(norm(int(x[i,k]))*norm(int(y[k,j])) for k in range(7))
                            for i in range(3) for j in range(4))
            self.assertLessEqual(ordinary, absolute_contraction_bound(x, y))
            self.assertLessEqual(component, absolute_contraction_bound(x, y, decomposed=True))

    def test_unsigned_reduction_overflow_never_becomes_a_small_bound(self):
        x = np.full((1, 5), (1 << 63)-1, dtype=np.int64)
        y = np.ones((5, 1), dtype=np.int64)
        self.assertEqual(absolute_contraction_bound(x, y), 5*((1 << 63)-1))
        with self.assertRaisesRegex(ValueError, 'S64'):
            ExactReferenceDot().dot({}, x, y)


if __name__ == '__main__':
    unittest.main()
