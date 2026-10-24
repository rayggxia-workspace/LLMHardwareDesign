"""Boundary tests use only bounded synthetic arrays; real model is server-only."""
import importlib.util
from pathlib import Path
import unittest
from fractions import Fraction
import tempfile
import numpy as np

spec = importlib.util.spec_from_file_location('granite', Path(__file__).with_name('granite.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GraniteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = Path('D:/Projects/Codex/moe-hybrid-20261024-1419/granite-tests')
        cls.temp.mkdir(parents=True, exist_ok=True)

    def test_error_identity(self):
        self.assertEqual(g.error([1., 2.], [1., 2.]), {'relative_l2': 0., 'max_abs': 0.})

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            g.error([np.nan], [0.])

    def test_shape_rejected(self):
        with self.assertRaises(ValueError):
            g.error([1., 2.], [[1., 2.]])

    def test_fixed_texts_separate(self):
        self.assertNotEqual(g.TEXTS['calibration'], g.TEXTS['evaluation'])

    def test_rne_signed_ties(self):
        for value in range(-129,130):
            for shift in range(0,8):
                self.assertEqual(g.rne_shift(value,shift),round(Fraction(value,2**shift)))
        self.assertEqual(g.rne_shift(-3,-2),-12)

    def test_quant_zero_and_saturation(self):
        q,s,sat = g.quantize([[0.,0.]])
        self.assertTrue(np.all(q==0)); self.assertTrue(np.all(s>0)); self.assertEqual(sat,0)
        q,s,sat = g.quantize([[-200.,-.5,.5,200.]],1.)
        np.testing.assert_array_equal(q,[[-127,0,0,127]])
        self.assertEqual(sat,2)

    def test_scale_invalid(self):
        for scale in (0.,-1.,np.nan):
            with self.assertRaises(ValueError):
                g.quantize([[1.]],scale)

    def test_topk_tie_is_low_index(self):
        ids,w = g.stable_topk(np.ones((1,40)))
        np.testing.assert_array_equal(ids,[list(range(8))])
        np.testing.assert_array_equal(w,np.full((1,8),.125))

    def test_dot_full_k(self):
        a = np.array([[127,-127,4]],dtype=np.int8)
        w = np.array([[127,127,-3],[-127,127,2]],dtype=np.int8)
        acc,bound = g.checked_dot(a,w)
        np.testing.assert_array_equal(acc,[[-12,-32250]])
        self.assertEqual(int(bound[0]),127*(127+127+3))

    def test_dot_dtype_and_int32_bound(self):
        with self.assertRaises(ValueError):
            g.checked_dot(np.ones((1,2)),np.ones((1,2)))
        # Actual bound exceeds 32 bits even though int64 software could compute it.
        a = np.full((1,140000),127,dtype=np.int8)
        with self.assertRaises(OverflowError):
            g.checked_dot(a,a)

    def test_q31_requant_half(self):
        m,s = g.q31_coefficients(np.asarray([.5,.25,2.,0.]))
        out,sat = g.requantize(np.array([5,-6,7,999]),m,s,32)
        np.testing.assert_array_equal(out,[2,-2,14,0])
        self.assertEqual(sat,0)

    def test_requant_saturation_and_product_guard(self):
        out,sat = g.requantize(np.array([-300,300]),np.array([1,1]),np.array([0,0]),8)
        np.testing.assert_array_equal(out,[-128,127]); self.assertEqual(sat,2)
        with self.assertRaises(OverflowError):
            g.requantize(np.array([2**62]),np.array([3]),np.array([0]),32)

    def test_deterministic_npz_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=self.temp) as tmp:
            p = Path(tmp)
            g.deterministic_npz(p/'a.npz',{'x':np.asarray([1,2])})
            g.deterministic_npz(p/'b.npz',{'x':np.asarray([1,2])})
            self.assertEqual(g.digest(p/'a.npz'),g.digest(p/'b.npz'))
            with self.assertRaises(FileExistsError):
                g.deterministic_npz(p/'a.npz',{})

    def test_silu_stable_at_extremes(self):
        y = g.silu(np.asarray([-1000.,0.,1000.]))
        np.testing.assert_array_equal(y,[0.,0.,1000.])


if __name__ == '__main__':
    unittest.main()
