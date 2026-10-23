"""Compare every accumulator against INT64 and output bits against prior real kernel."""
import unittest
import torch
from kernel import BatchedInt8,install,grouped

class BatchedChecks(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(),'requires actual GPU')
    def test_all_accumulators_exact(self):
        a=torch.randint(-127,128,(4,32,32),device='cuda',dtype=torch.int8)
        b=torch.randint(-127,128,(4,32,256),device='cuda',dtype=torch.int8)
        result=BatchedInt8().mm(a,b).cpu().long()
        expected=torch.stack([x.long()@y.long() for x,y in zip(a.cpu(),b.cpu())])
        self.assertTrue(torch.equal(result,expected))

    @unittest.skipUnless(torch.cuda.is_available(),'requires actual GPU')
    def test_outputs_bitwise_same_as_old_group_kernel(self):
        for k in (32,128):
            torch.manual_seed(34)
            old=torch.nn.Sequential(torch.nn.Linear(256,256,device='cuda',dtype=torch.float16))
            new=torch.nn.Sequential(torch.nn.Linear(256,256,device='cuda',dtype=torch.float16))
            new.load_state_dict(old.state_dict())
            with torch.inference_mode():
                grouped.install(old,'raw',{},k);install(new,'raw',{},k)
                for n in (1,129):
                    x=torch.randn(1,n,256,device='cuda',dtype=torch.float16)
                    self.assertTrue(torch.equal(old(x),new(x)),(k,n))

if __name__=='__main__':unittest.main()
