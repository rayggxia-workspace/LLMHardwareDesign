"""Tiny synthetic tests only; never load a model or real capture locally."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_capture74',Path(__file__).with_name('granite_capture.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class CaptureTests(unittest.TestCase):
    def test_selected_expert_actual_intermediates(self):
        import torch
        import torch.nn.functional as F
        from types import SimpleNamespace
        x=torch.tensor([[1.,-1.,2.],[2.,1.,-3.]],dtype=torch.float64)
        ids=torch.tensor([[0,1],[1,0]])
        gates=torch.tensor([[.25,.75],[.5,.5]],dtype=torch.float64)
        up=torch.arange(24,dtype=torch.float64).reshape(2,4,3)/100
        down=torch.arange(12,dtype=torch.float64).reshape(2,3,2)/50
        records={}
        module=SimpleNamespace(num_experts=2,gate_up_proj=up,down_proj=down,act_fn=F.silu,_issue74_capture=records)
        y=g.selected_experts(module,x,ids,gates)
        expected=torch.zeros_like(y)
        for token in range(2):
            for rank in range(2):
                e=int(ids[token,rank]);a,b=F.linear(x[token],up[e]).chunk(2,dim=-1)
                mid=F.silu(a)*b;z=F.linear(mid,down[e])
                np.testing.assert_allclose(records['expert_gate'][token,rank],a.numpy(),rtol=1e-14,atol=1e-14)
                np.testing.assert_allclose(records['expert_mid'][token,rank],mid.numpy(),rtol=1e-14,atol=1e-14)
                np.testing.assert_allclose(records['expert_down'][token,rank],z.numpy(),rtol=1e-14,atol=1e-14)
                expected[token]+=z*gates[token,rank]
        torch.testing.assert_close(y,expected,rtol=1e-14,atol=1e-14)
        self.assertEqual(records['expert_down'].shape,(2,2,3))

    def test_layers_and_original_gate(self):
        self.assertEqual(g.LAYERS,(0,13))
        self.assertEqual(g.GATE,{'relative_l2_max':2e-4,'max_abs_max':2e-3})

    def test_metric_finite_shape(self):
        self.assertEqual(g.metric([1.,2.],[1.,2.]),{'relative_l2':0.,'max_abs':0.})
        with self.assertRaises(ValueError):g.metric([np.inf],[1.])
        with self.assertRaises(ValueError):g.metric([1.],[1.,2.])

if __name__=='__main__':unittest.main()
