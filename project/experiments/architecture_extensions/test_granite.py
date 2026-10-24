"""Boundary tests use only bounded synthetic arrays; real model is server-only."""
import importlib.util
from pathlib import Path
import unittest
from fractions import Fraction
import copy
import tempfile
import numpy as np

spec = importlib.util.spec_from_file_location('granite', Path(__file__).with_name('granite.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
dspec=importlib.util.spec_from_file_location('granite_diagnose',Path(__file__).with_name('granite_diagnose.py'))
d=importlib.util.module_from_spec(dspec);dspec.loader.exec_module(d)


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

    def test_route_diagnostic_set_and_rank_are_separate(self):
        logits=np.asarray([[4.,3.,2.,1.]])
        rank=d.compare_routes(logits,np.asarray([[0,1]]),logits,np.asarray([[1,0]]))
        self.assertEqual(rank['set_changed_tokens'],0)
        self.assertEqual(rank['ordered_changed_tokens'],1)
        flipped=d.compare_routes(logits,np.asarray([[0,1]]),np.asarray([[4.,2.,3.,1.]]),np.asarray([[0,2]]))
        self.assertEqual(flipped['set_changed_tokens'],1)
        self.assertEqual(flipped['changes'][0]['replaced_experts'],1)
        self.assertEqual(flipped['changes'][0]['full_margin'],1.)

    def test_route_diagnostic_near_boundary(self):
        full=np.asarray([[3.,1.,1.-1e-7,0.]])
        other=np.asarray([[3.,1.-1e-7,1.,0.]])
        diff=d.compare_routes(full,np.asarray([[0,1]]),other,np.asarray([[0,2]]))
        self.assertAlmostEqual(diff['minimum_full_top8_margin'],1e-7)
        self.assertEqual(diff['changes'][0]['position'],0)

    def failed_chunk_fixture(self):
        case={'batch':1,'prefill':64,'decode':8,'tokens':list(range(72)),
              'cached':{'relative_l2':1e-6,'max_abs':1e-4},
              'moe_replay':{'relative_l2':1e-7,'max_abs':1e-5},
              'chunk16':{'relative_l2':1e-6,'max_abs':1e-4},'passed':True}
        cal=copy.deepcopy(case);ev=copy.deepcopy(case)
        ev['chunk16']={'relative_l2':.0058,'max_abs':1.18};ev['passed']=False
        return {'kind':'granite_capture','status':'FAIL',
                'correctness_gate':{'relative_l2_max':2e-4,'max_abs_max':2e-3,'passed':False},
                'cases':{'calibration':cal,'evaluation':ev}}

    def test_partial_capture_requires_explicit_flag_and_retains_failure(self):
        source=self.failed_chunk_fixture()
        with self.assertRaises(ValueError):
            g.qualify_capture(source)
        q=g.qualify_capture(source,True)
        self.assertEqual(q['capture_status'],'FAIL')
        self.assertEqual(q['failed_checks'][0]['check'],'evaluation.chunk16')
        self.assertFalse(q['quality_accepted']);self.assertFalse(q['chunk_reference_accepted'])
        self.assertEqual(source['status'],'FAIL')

    def test_partial_does_not_allow_other_failures_or_gate_changes(self):
        for path,value in [(('cases','calibration','cached','max_abs'),.1),
                           (('cases','evaluation','moe_replay','relative_l2'),.1),
                           (('cases','calibration','chunk16','max_abs'),.1),
                           (('correctness_gate','max_abs_max'),2.),
                           (('cases','evaluation','passed'),True)]:
            source=self.failed_chunk_fixture();obj=source
            for key in path[:-1]:obj=obj[key]
            obj[path[-1]]=value
            with self.assertRaises(ValueError):g.qualify_capture(source,True)


if __name__ == '__main__':
    unittest.main()
