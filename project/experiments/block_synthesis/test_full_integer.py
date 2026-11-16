import unittest
import numpy as np
from full_integer import round_shift
from sigmoid_polynomial import coefficients,evaluate,exp_coefficients


class TestIntegerMath(unittest.TestCase):
    def test_signed_rounding_and_left_scale_do_not_lose_wide_bits(self):
        self.assertEqual(round_shift(np.array([1,3,5,-1,-3,-5]),1).tolist(),[0,2,2,0,-2,-2])
        self.assertEqual(round_shift(np.array([20000,-20000]),-12).tolist(),[81920000,-81920000])
        with self.assertRaises(ValueError):round_shift(np.array([1<<62]),-2)

    def test_offline_polynomial_coefficients_and_s32_interval(self):
        t=np.linspace(-1,1,65537)
        raw=np.rint(t*(1<<30)).astype(np.int64)
        actual=evaluate(raw,coefficients())/(1<<30)
        expected=1/(1+np.exp(-4*t))
        self.assertLess(float(np.abs(actual-expected).max()),2e-6)
        with self.assertRaises(ValueError):evaluate([1+(1<<30)],coefficients())

    def test_signed_two_part_identity_including_tie_patterns(self):
        vals=np.array([-8388608,-65536,-32768,-1,0,32767,32768,65535,65536,8388607],dtype=np.int64)
        lo=(vals&65535).astype(np.uint16).view(np.int16).astype(np.int64)
        hi=(vals>>16)+(lo<0)
        np.testing.assert_array_equal(lo+(hi<<16),vals)
        self.assertTrue(np.all((hi>=-32768)&(hi<=32767)))

    def test_exponential_coefficients_and_s32_clenshaw_state(self):
        t=np.linspace(-1,1,65537);raw=np.rint(t*(1<<30)).astype(np.int64)
        actual=evaluate(raw,exp_coefficients())/(1<<28)
        self.assertLess(float(np.abs(actual-np.exp(8*t-8)).max()),2e-7)
        self.assertTrue(np.all(actual>=0))


if __name__=='__main__':unittest.main()
