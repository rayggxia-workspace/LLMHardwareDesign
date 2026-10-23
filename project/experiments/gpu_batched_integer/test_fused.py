import unittest
import torch
import fused

class FusedChecks(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(),'actual CUDA required')
    def test_fp32_partial_order_and_accumulator_max(self):
        for k in (32,128):
            torch.manual_seed(41)
            a=torch.nn.Sequential(torch.nn.Linear(256,256,device='cuda',dtype=torch.float16))
            b=torch.nn.Sequential(torch.nn.Linear(256,256,device='cuda',dtype=torch.float16))
            b.load_state_dict(a.state_dict())
            with torch.inference_mode():
                fused.base.grouped.install(a,'raw',{},k);fused.install(b,'raw',{},k)
                for dtype in (torch.float16,torch.float32):
                    for n in (1,129):
                        x=torch.randn(1,n,256,device='cuda',dtype=dtype)
                        self.assertTrue(torch.equal(a(x),b(x)),(k,n,dtype))
                self.assertEqual(a[0].stats['max_abs_acc'],b[0].stats['max_abs_acc'])

if __name__=='__main__':unittest.main()
