"""Small synthetic tests only; no model download/load in local tests."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_reference',Path(__file__).with_name('granite_reference.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class ReferenceTests(unittest.TestCase):
    def test_spans_are_causal_exact_cover(self):
        for profile in g.PROFILES:
            spans=g.spans(profile)
            self.assertEqual([i for a,b in spans for i in range(a,b)],list(range(72)))
        self.assertEqual(g.spans('cached64')[0],(0,64))
        self.assertEqual(g.spans('chunk16')[-1],(64,72))
        with self.assertRaises(ValueError):g.spans('bad')

    def test_margin_preserves_near_tie(self):
        x=np.arange(40,dtype=np.float64)[None,:]
        x[0,31]=x[0,32]-2.0**-30
        ids=np.argsort(-x,axis=-1,kind='stable')[:,:8]
        s=g.routing_summary(x,ids)
        self.assertEqual(s['exact_cutoff_tie_tokens'],0)
        self.assertAlmostEqual(s['minimum_top8_margin'],2.0**-30)

    def test_exact_cutoff_tie_reported(self):
        x=np.arange(40,dtype=np.float64)[None,:]
        x[0,31]=32
        ids=np.argsort(-x,axis=-1,kind='stable')[:,:8]
        self.assertEqual(g.routing_summary(x,ids)['exact_cutoff_tie_tokens'],1)
        self.assertEqual(ids[0,-1],31)

    def test_invalid_routes_rejected(self):
        x=np.arange(40,dtype=float)[None,:]
        for ids in (np.arange(8)[None,:],np.full((1,8),39)):
            with self.assertRaises(ValueError):g.routing_summary(x,ids)
        with self.assertRaises(ValueError):g.routing_summary(np.zeros((1,39)),np.arange(8)[None,:])

    def test_route_replacement_not_just_order(self):
        x=np.arange(40,dtype=float)[None,:]
        a=np.argsort(-x,axis=-1)[:,:8]
        y=x.copy();y[0,31]=39.5
        b=np.argsort(-y,axis=-1)[:,:8]
        result=g.route_comparison(x,a,y,b)
        self.assertEqual(result['set_changed_tokens'],1)
        self.assertEqual(result['replaced_experts'],[1])

    def test_original_gate_unmodified(self):
        self.assertEqual(g.GATE,{'relative_l2_max':2e-4,'max_abs_max':2e-3})

    def test_metric_rejects_nonfinite_shape(self):
        for a,b in (([np.inf],[1.]),([1.],[1.,2.]),([],[])):
            with self.assertRaises(ValueError):g.metric(a,b)

    def test_fp64_experts_stay_double_and_match_direct_sum(self):
        import torch
        import torch.nn.functional as F
        from types import SimpleNamespace
        wup=torch.arange(2*4*3,dtype=torch.float64).reshape(2,4,3)/100
        wdown=torch.arange(2*3*2,dtype=torch.float64).reshape(2,3,2)/50
        x=torch.tensor([[1.,-1.,2.],[2.,1.,-3.]],dtype=torch.float64)
        ids=torch.tensor([[0,1],[1,0]])
        gate=torch.tensor([[.25,.75],[.5,.5]],dtype=torch.float64)
        e=SimpleNamespace(num_experts=2,gate_up_proj=wup,down_proj=wdown,act_fn=F.silu)
        expected=torch.zeros_like(x)
        for row in range(2):
            for rank in range(2):
                i=int(ids[row,rank]);a,b=F.linear(x[row],wup[i]).chunk(2,dim=-1)
                expected[row]+=F.linear(F.silu(a)*b,wdown[i])*gate[row,rank]
        actual=g.explicit_eager_experts(e,x,ids,gate)
        self.assertEqual(actual.dtype,torch.float64)
        torch.testing.assert_close(actual,expected,rtol=1e-14,atol=1e-14)

    def test_fp64_top8_retains_distinct_near_tie(self):
        import torch
        from types import SimpleNamespace
        w=torch.arange(40,dtype=torch.float64)[:,None]
        w[31]=w[32]-2.0**-30
        module=SimpleNamespace(weight=w,top_k=8)
        ids,weights,logits=g.high_precision_router(module,torch.ones((1,1),dtype=torch.float64))
        self.assertEqual(logits.dtype,torch.float64)
        self.assertEqual(ids[0,-1].item(),32)
        self.assertNotIn(31,ids[0].tolist())
        w[31]=w[32]
        ids,_,_=g.high_precision_router(module,torch.ones((1,1),dtype=torch.float64))
        self.assertEqual(ids[0,-1].item(),31)

if __name__=='__main__':unittest.main()
