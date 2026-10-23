import importlib.util
from pathlib import Path
import unittest
import torch

spec=importlib.util.spec_from_file_location('canonical_aux_tests',Path(__file__).resolve().parents[1]/'gpu_state_repair/canonical.py')
canonical=importlib.util.module_from_spec(spec);spec.loader.exec_module(canonical)

class CanonicalChecks(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(),'actual CUDA required')
    def test_norm_conv_and_recurrence_call_boundary_invariance(self):
        from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
        torch.manual_seed(43)
        norm=impl.Qwen3_5RMSNorm(2560).cuda().float()
        canonical.install(torch.nn.Sequential(norm))
        with torch.inference_mode():
            x=torch.randn(1,129,2560,device='cuda')
            whole=norm(x);split=torch.cat([norm(x[:,i:i+1]) for i in range(129)],dim=1)
            self.assertTrue(torch.equal(whole,split))
            x=torch.randn(1,8,129,device='cuda');w=torch.randn(8,4,device='cuda')
            whole=impl.causal_conv1d_fn(x,w,None,activation='silu')
            conv=torch.zeros(1,8,4,device='cuda')
            split=torch.cat([impl.causal_conv1d_update(x[...,i:i+1],conv,w,None,'silu') for i in range(129)],dim=-1)
            self.assertTrue(torch.equal(whole,split))
            q,k,v=[torch.randn(1,129,2,128,device='cuda') for _ in range(3)]
            g=-torch.rand(1,129,2,device='cuda');beta=torch.rand_like(g)
            kw=dict(output_final_state=True,use_qk_l2norm_in_kernel=True)
            whole,last=impl.torch_recurrent_gated_delta_rule(q,k,v,g=g,beta=beta,**kw)
            parts=[];s=None
            for start in range(0,129,32):
                end=min(129,start+32)
                part,s=impl.torch_recurrent_gated_delta_rule(q[:,start:end],k[:,start:end],v[:,start:end],
                    g=g[:,start:end],beta=beta[:,start:end],initial_state=s,**kw)
                parts.append(part)
            self.assertTrue(torch.equal(last,s));self.assertTrue(torch.equal(whole,torch.cat(parts,dim=1)))

if __name__=='__main__':unittest.main()
