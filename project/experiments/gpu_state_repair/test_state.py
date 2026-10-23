"""Wide-code rounding and logical versus allocated storage use independent FP64 NumPy."""
import types
import unittest
import numpy as np
import torch
from run import perturb

class StateChecks(unittest.TestCase):
    def test_wide_quantizer_codes_and_unpacked_storage(self):
        for bits in (24,32):
            values=torch.tensor([1.0,-.99,1e-4,-.00317],dtype=torch.float32).reshape(1,1,1,4)
            original=values.clone()
            cache=types.SimpleNamespace(layers=[types.SimpleNamespace(recurrent_states={0:values})])
            bound=(1<<(bits-1))-1
            scale=np.float32(np.max(np.abs(original.numpy()))/bound)
            codes=np.clip(np.rint(original.numpy().astype(np.float64)/float(scale)),-bound,bound).astype(np.int32)
            expected=(codes.astype(np.float64)*float(scale)).astype(np.float32)
            rows=perturb(cache,'recurrent',bits)
            self.assertTrue(np.array_equal(values.numpy(),expected))
            self.assertEqual(rows[0]['payload_bytes'],values.numel()*(bits//8))
            self.assertEqual(rows[0]['quantizer_code_allocation_bytes'],values.numel()*4)

if __name__=='__main__':unittest.main()
