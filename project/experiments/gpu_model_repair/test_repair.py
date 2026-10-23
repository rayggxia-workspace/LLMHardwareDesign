"""Check candidate arithmetic and fixed acceptance using an independent integer sum."""
import unittest
import torch
from run import install,quality_pass

class RepairChecks(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(),'requires actual CUDA integer kernel')
    def test_actual_integer_scale_and_bias(self):
        torch.manual_seed(12)
        m=torch.nn.Sequential(torch.nn.Linear(16,8,bias=True,device='cuda',dtype=torch.float16))
        x=torch.randn(1,3,16,device='cuda',dtype=torch.float16)
        with torch.inference_mode():
            install(m,'raw',{})
            actual=m(x)
            layer=m[0]
            xf=x.reshape(-1,16).float()
            scale=xf.abs().amax(-1,keepdim=True)/127
            qa=(xf/scale).round().clamp(-127,127).long().cpu()
            acc=qa@layer.qweight.long().cpu()
            expected=(acc.float().cuda()*scale*layer.wscale+layer.bias.float()).half().reshape_as(actual)
        self.assertTrue(torch.equal(actual,expected))
        self.assertEqual(layer.stats['saturation_count'],0)
        self.assertEqual(layer.stats['calls'],1)

    def test_acceptance_keeps_bad_distribution_failure(self):
        cfg={'quality_acceptance':{'mean_kl_max':.05,'nll_delta_max':.15,'top1_agreement_min':.9}}
        row={'finite':True,'mean_kl':.1,'nll_delta':-.2,'top1_agreement':.95}
        self.assertFalse(quality_pass(row,cfg))

if __name__=='__main__':unittest.main()
