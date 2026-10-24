"""Small independent mathematical tests, not real Granite tensors."""
from fractions import Fraction
import math
import unittest
import numpy as np

from receive_granite import IntegerMath, i32


class GraniteIntegerMathTests(unittest.TestCase):
    def test_dynamic_rne_not_truncation_and_minimal(self):
        engine = IntegerMath()
        values = np.asarray([[-255, -253, 253, 255], [-1, 0, 1, 2]], np.int32)
        code, delta = engine.dynamic(values)
        self.assertTrue(np.array_equal(delta, [2, 0]))
        self.assertTrue(np.array_equal(code, [[-64, -63, 63, 64], [-1, 0, 1, 2]]))
        for shift in (1, 2, 63, 64):
            expected = [round(Fraction(int(x), 1 << shift)) for x in values.flat]
            self.assertTrue(np.array_equal(engine.shift(values, shift), np.asarray(expected).reshape(values.shape)))

    def test_complete_dot_then_single_q31_rounding(self):
        engine = IntegerMath()
        x = np.asarray([[512, -256, 128], [-256, 128, 64]], np.int32)
        w = np.asarray([[3, -2, 1], [-4, 3, -2]], np.int8)
        mantissa = np.asarray([1 << 30, 1 << 30], np.int32)
        exponent = np.asarray([1, 0], np.int16)
        actual, trace = engine.linear(x, w, mantissa, exponent)
        for row in range(2):
            for col in range(2):
                dot = sum(int(a) * int(b) for a, b in zip(trace["a8"][row], w[col]))
                numerator = dot * int(mantissa[col])
                shift = 31-int(exponent[col])-int(trace["delta"][row])
                self.assertEqual(actual[row, col], round(Fraction(numerator, 1 << shift)))

    def test_full_norm_integer_denominator(self):
        x = np.asarray([[4096, -8192, 2048, 0]], np.int32)
        gamma = np.asarray([1 << 20, 1 << 19, 1 << 20, 1 << 20], np.int32)
        got, trace = IntegerMath().norm(x, gamma, 17)
        variance = sum(int(v)**2 for v in x[0]) // 4 + 17
        denominator = math.isqrt(variance << 40)
        self.assertEqual(trace["denominator"], [denominator])
        expected = [round(Fraction(int(v)*int(g)*(1 << 12), denominator)) for v, g in zip(x[0], gamma)]
        self.assertTrue(np.array_equal(got[0], expected))

    def test_merge_complete_eight_before_one_round(self):
        expert = np.asarray([[[1, -1]] * 8], np.int32)
        gates = np.full((1, 8), 4096, np.uint16)
        result, prefixes = IntegerMath().merge(expert, gates)
        self.assertTrue(np.array_equal(result, [[1, -1]]))
        self.assertTrue(np.array_equal(prefixes[0, -1], [32768, -32768]))
        # Rounding each weighted return first would incorrectly return zero.
        self.assertEqual(sum(round(Fraction(4096, 32768)) for _ in range(8)), 0)

    def test_i32_and_intermediate_overflow_rejected(self):
        with self.assertRaises(ValueError):
            i32(np.asarray([1 << 31], np.int64))
        with self.assertRaises(ValueError):
            IntegerMath().product(np.asarray([1 << 62]), np.asarray([4]))

    def test_router_all_rows_nine_dot_and_integer_ties(self):
        x = np.asarray([[32767, -32767, 1024], [-32768, 0, 1]], np.int32)
        weight = np.zeros((40, 3), np.int16)
        weight[0], weight[1], weight[2] = [32767, -32767, 1], [32767, -32767, 1], [-32767, 1, 0]
        table = np.asarray([round((2.0**(-i/128))*(1 << 24)) for i in range(2049)], np.uint32)
        trace = IntegerMath().router(x, weight, np.zeros(40, np.int16), 16, table)
        self.assertEqual(trace["partials"].shape, (9, 2, 40))
        self.assertEqual(trace["ids"][0, :2].tolist(), [0, 1])
        self.assertTrue(np.array_equal(trace["gate_q15"].astype(np.int64).sum(axis=1), [32768, 32768]))
        self.assertEqual(trace["input_delta"][1], 1)


if __name__ == "__main__":
    unittest.main()
