"""Independent route receiver tests; no model or producer imports."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('verify_diagnose',Path(__file__).with_name('verify_diagnose.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class DiagnoseReceiverTests(unittest.TestCase):
    def test_native_top8_complete_and_wrong_set(self):
        logits=np.arange(40,dtype=np.float32)[None,:]
        ids=np.asarray([list(range(39,31,-1))])
        v.validate_native_topk(logits,ids)
        bad=ids.copy();bad[0,-1]=0
        with self.assertRaises(ValueError):v.validate_native_topk(logits,bad)

    def test_exact_tie_allows_native_arbitrary_cutoff_choice(self):
        logits=np.ones((1,40),dtype=np.float32)
        ids=np.asarray([[32,7,2,19,38,5,15,0]])
        v.validate_native_topk(logits,ids)
        bad=ids.copy();bad[0,-1]=bad[0,0]
        with self.assertRaises(ValueError):v.validate_native_topk(logits,bad)

    def test_fp32_softmax_consistency_and_negative(self):
        logits=np.arange(40,dtype=np.float32)[None,:]
        ids=np.asarray([list(range(39,31,-1))])
        weights=np.exp(np.arange(0,-8,-1,dtype=np.float64));weights=(weights/weights.sum()).astype(np.float32)[None,:]
        v.validate_weights(logits,ids,weights)
        with self.assertRaises(ValueError):v.validate_weights(logits,ids,np.full((1,8),.125))

    def test_set_changes_rank_and_near_margin_independent(self):
        full=np.zeros((1,40),dtype=np.float32)
        full[0,:7]=np.arange(10,3,-1);full[0,7]=1.;full[0,8]=np.nextafter(np.float32(1.),np.float32(0.))
        other=full.copy();other[0,7],other[0,8]=other[0,8],other[0,7]
        ids=np.asarray([list(range(8))]);oid=np.asarray([[0,1,2,3,4,5,6,8]])
        r=v.route_comparison(full,ids,other,oid)
        self.assertEqual(r['set_changed_tokens'],1)
        self.assertEqual(r['changes'][0]['replaced_experts'],1)
        self.assertEqual(r['changes'][0]['full_margin'],float(np.float32(1.)-np.nextafter(np.float32(1.),np.float32(0.))))

    def test_report_forged_margin_or_first_change_rejected(self):
        expected={'first_layer':13,'margin':2.9802322387695312e-8}
        v.numbers_close(dict(expected),expected,'report')
        with self.assertRaises(ValueError):v.numbers_close({'first_layer':12,'margin':expected['margin']},expected,'report')
        with self.assertRaises(ValueError):v.numbers_close({'first_layer':13,'margin':.001},expected,'report')

    def test_final_error_independent_identity(self):
        self.assertEqual(v.independent_error([1.,2.],[1.,2.]),{'relative_l2':0.,'max_abs':0.})
        with self.assertRaises(ValueError):v.independent_error([np.nan],[1.])


if __name__=='__main__':
    unittest.main()
