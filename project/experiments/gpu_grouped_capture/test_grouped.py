"""Exact independent sums for group selection, bias and non-tile row counts."""
import importlib.util
from pathlib import Path
import unittest
import torch

spec=importlib.util.spec_from_file_location('test_grouped_candidate',Path(__file__).resolve().parents[1]/'gpu_grouped_repair/run.py')
grouped=importlib.util.module_from_spec(spec);spec.loader.exec_module(grouped)

class GroupChecks(unittest.TestCase):
    def test_two_group_formats_and_bias(self):
        for k in (32,128):
            torch.manual_seed(7)
            m=torch.nn.Sequential(torch.nn.Linear(256,8,bias=True,dtype=torch.float16))
            x=torch.randn(1,3,256,dtype=torch.float16)
            with torch.inference_mode():
                grouped.install(m,'raw',{},group_k=k)
                actual=m(x);layer=m[0]
                expected=torch.zeros(3,8)
                for g in range(256//k):
                    block=x.reshape(3,256)[:,g*k:(g+1)*k].float()
                    scale=block.abs().amax(-1,keepdim=True)/127
                    a=(block/scale).round().clamp(-127,127).long()
                    exact=a@layer.qblocks[g].long()
                    expected+=exact.float()*scale*layer.wscales[g]
                expected=(expected+layer.bias.float()).half().reshape_as(actual)
            self.assertTrue(torch.equal(actual,expected),k)
            self.assertEqual(layer.stats['int8_gemm_calls'],256//k)
            self.assertEqual(layer.stats['saturation_count'],0)

if __name__=='__main__':unittest.main()
