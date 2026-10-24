import unittest
import numpy as np
from wide_product import multiply_bytes, words


class WideProductBoundary(unittest.TestCase):
    def check(self, aa, bb, width):
        a = np.asarray(aa, np.int64)
        b = np.asarray(bb, np.int64)
        result, counts = multiply_bytes(a, b, width)
        hi, lo = words(result)
        expected = [int(x) * int(y) for x, y in zip(a, b)]
        self.assertEqual([(int(h) << 64) | int(l) for h, l in zip(hi, lo)], expected)
        self.assertEqual(counts["S8_products"], len(a) * (25 if width == 32 else 45))
        self.assertEqual(counts["core_byte_lane_slots"], len(a) * (265 if width == 32 else 837))

    def test_i32_endpoints_and_carry(self):
        self.check([-(1 << 31), (1 << 31) - 1, -1, 0, 127, -128],
                   [-(1 << 31), (1 << 31) - 1, -1, 0, -128, 127], 32)

    def test_i64_endpoints_and_sign_extension(self):
        self.check([-(1 << 63), (1 << 63) - 1, -1, 0, 1 << 50, -(1 << 50)],
                   [-(1 << 31), -(1 << 31), (1 << 31) - 1, -1, -3, 3], 64)

    def test_random_fixed_seed(self):
        rng = np.random.default_rng(74)
        for width in (32, 64):
            a = rng.integers(-(1 << (width - 2)), (1 << (width - 2)), 39, dtype=np.int64)
            b = rng.integers(-(1 << 31), (1 << 31) - 1, 39, dtype=np.int64)
            self.check(a, b, width)

    def test_refuse_undeclared_width(self):
        with self.assertRaises(ValueError):
            multiply_bytes(np.array([1 << 31]), np.array([1]), 32)
        with self.assertRaises(ValueError):
            multiply_bytes(np.array([1]), np.array([1 << 31]), 64)


if __name__ == "__main__":
    unittest.main()
