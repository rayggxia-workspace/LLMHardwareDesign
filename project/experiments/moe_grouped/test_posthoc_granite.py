"""Tiny synthetic tests only; never loads real model captures on the PC."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('posthoc74',Path(__file__).with_name('posthoc_granite.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def case():
    product=np.array([[[2048,2049,0],[-2048,-6144,4096]],[[0,1,2],[8192,4096,-4096]]],np.int64)
    mid=m.rne(product,12).astype(np.int32)
    actual=np.array([[2,1],[3,0]],np.uint8);native=np.array([[1,2],[1,0]],np.int64)
    logits=np.array([[0.,2.,3.,1.],[2.,1.,0.,3.]])
    trace={'router.ids':actual,'expert_mid_q12':mid,'mid_product64':product,'mid_a8':mid.astype(np.int8),
        'mid_delta':np.zeros((2,2),np.int16),'down_q12':np.ones((2,2,4),np.int32),
        'router.gate_q15':np.full((2,2),16384,np.uint16)}
    ref={'x.ids':native,'x.expert_mid':np.array([[[.0001,-.0002,.001],[.00005,.0002,0]],
        [[.003,.002,.001],[.0001,.0001,.0001]]]),'x.expert_down':np.ones((2,2,4))/4096,
        'x.gate':np.full((2,2),.5)}
    diag={'same_current_norm_FP64_logits':logits,'same_current_norm_FP64_ids':np.argsort(-logits,axis=1,kind='stable')[:,:2]}
    return trace,ref,diag


class Tests(unittest.TestCase):
    def test_signed_ties_even(self):
        x=np.array([-10240,-6144,-2048,0,2048,6144,10240],np.int64)
        np.testing.assert_array_equal(m.rne(x,12),[-2,-2,0,0,0,2,2])
        np.testing.assert_array_equal(m.rne(x,0),x)
        with self.assertRaises(OverflowError):m.rne(np.array([-(1<<63)],np.int64),1)

    def test_ID_matching_and_all_path_denominators(self):
        t,r,d=case();report,w=m.analyze(t,r,d,'x.',4)
        np.testing.assert_array_equal(w['native_rank_for_runtime_ID'],[[1,0],[-1,1]])
        self.assertEqual(report['all']['paths'],4)
        self.assertEqual(report['all']['matched_native_ID_paths'],3)
        self.assertEqual(report['all']['mid_Q12_vs_native_matched']['elements'],9)
        self.assertEqual(report['all']['down_Q12_vs_native_matched']['max_abs'],0.)
        self.assertEqual(w['native_mid_sse'][1,0],0.)
        self.assertEqual(report['all']['routes']['native_to_same_current_norm_FP64'],1)
        self.assertEqual(report['all']['routes']['same_current_norm_FP64_to_integer'],0)
        self.assertEqual(report['all']['runtime_gate_mass_unmatched_experts'],.5)
        self.assertEqual(len(report['per_token']),2)
        self.assertEqual(report['per_token'][1]['mid_delta_8paths'],[0,0])

    def test_rounding_loss_decomposition(self):
        t,r,d=case();report,w=m.analyze(t,r,d,'x.',4)
        energy=report['all']['matched_mid_error_decomposition']
        self.assertAlmostEqual(energy['identity_residual'],0.,places=18)
        self.assertGreater(energy['same_operand_final_Q12_RNE_sse'],0.)
        self.assertEqual(report['all']['allpath_additional_A8_loss']['max_abs'],0.)
        self.assertEqual(report['all']['allpath_product_nonzero_to_Q12_zero'],4)
        self.assertEqual(w['product_nonzero_to_Q12_zero_count'][1,0],2)

    def test_modified_rounding_is_rejected(self):
        t,r,d=case();t['expert_mid_q12'][0,0,0]=1
        with self.assertRaisesRegex(ValueError,'RNE inconsistency'):m.analyze(t,r,d,'x.',4)

    def test_modified_A8_is_rejected(self):
        t,r,d=case();t['mid_a8'][0,0,0]=1
        with self.assertRaisesRegex(ValueError,'A8 RNE inconsistency'):m.analyze(t,r,d,'x.',4)

    def test_duplicate_ids_and_diagnostic_corruption(self):
        t,r,d=case();t['router.ids'][0]=[1,1]
        with self.assertRaisesRegex(ValueError,'distinct'):m.analyze(t,r,d,'x.',4)
        t,r,d=case();d['same_current_norm_FP64_ids'][0]=[1,2]
        with self.assertRaisesRegex(ValueError,'diagnostic topk'):m.analyze(t,r,d,'x.',4)

    def test_gate_unsigned_full_range(self):
        t,r,d=case();t['router.gate_q15'][:]=[32768,0]
        report,w=m.analyze(t,r,d,'x.',4)
        self.assertEqual(w['runtime_gate_Q15_decoded'][0,0],1.)
        t['router.gate_q15'][0,0]=32767
        with self.assertRaisesRegex(ValueError,'complete sum'):m.analyze(t,r,d,'x.',4)


if __name__=='__main__':unittest.main()
