"""Unit checks of quantization/metric plumbing, not small-model research results."""
import unittest
from types import SimpleNamespace
import torch
from run import install_int8, fake_state, output_metrics
from verify import recurrent


class ProtocolTests(unittest.TestCase):
    def test_state_rounding_and_scale_cost(self):
        x=torch.tensor([[[[0.,1.,-2.],[0.5,1.5,2.]]]])
        cache=SimpleNamespace(layers=[SimpleNamespace(recurrent_states=[x])])
        rows=fake_state(cache,8)
        self.assertEqual(rows[0]['scale_bytes'],4)
        self.assertEqual(rows[0]['quantized_payload_bytes'],6)
        self.assertTrue(torch.isfinite(x).all())
        self.assertLess(rows[0]['max_abs'],2/127)

    def test_distribution_identity_and_error(self):
        x=torch.tensor([[[2.,0.,-1.],[0.,3.,1.]]]); labels=torch.tensor([[0,1]])
        self.assertEqual(output_metrics(x,x,labels)['mean_kl'],0)
        self.assertEqual(output_metrics(x,x,labels)['top1_agreement'],1)
        self.assertGreater(output_metrics(-x,x,labels)['mean_kl'],1)

    def test_real_integer_kernel_matches_independent_sum(self):
        # This kernel/API test uses integer operands and an independent INT64 sum.
        a=torch.arange(32*32).reshape(32,32).remainder(255).sub(127).to(torch.int8)
        b=torch.flip(a,[0]).contiguous()
        expected=(a.long()[:,:,None]*b.long()[None,:,:]).sum(1)
        self.assertTrue(torch.equal(torch._int_mm(a,b).long(),expected))

    def test_recurrent_wrong_initial_state_changes_result(self):
        p={'query':torch.ones(1,1,1,2),'key':torch.tensor([[[[1.,0.]]]]),
           'value':torch.ones(1,1,1,2),'g':torch.zeros(1,1,1),'beta':torch.ones(1,1,1)*0.5,
           'initial_state':torch.zeros(1,1,2,2),'use_qk_l2norm_in_kernel':True,
           'output':torch.ones(1,1,1,2)}
        _,good=recurrent(p);_,bad=recurrent(p,True)
        self.assertFalse(torch.equal(good,bad))


if __name__=='__main__': unittest.main()
