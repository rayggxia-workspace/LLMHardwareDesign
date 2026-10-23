import unittest
import numpy as np
import torch
from transformers import DynamicCache
from transformers.models.gemma3.configuration_gemma3 import Gemma3TextConfig
from capture import allowed_mask,kv_record


class CacheContract(unittest.TestCase):
    def test_sliding_mask_boundary(self):
        got=allowed_mask(np.array([3,4,5]),np.arange(6),4)
        self.assertEqual(got.astype(int).tolist(),[[1,1,1,1,0,0],[0,1,1,1,1,0],[0,0,1,1,1,1]])
        self.assertFalse(allowed_mask(np.array([1]),np.array([2]),None)[0,0])

    def test_native_tiny_cache_storage_is_explicit(self):
        cfg=Gemma3TextConfig(hidden_size=8,intermediate_size=16,num_attention_heads=2,num_key_value_heads=1,
            head_dim=4,num_hidden_layers=6,sliding_window=4)
        cache=DynamicCache(config=cfg)
        x=torch.arange(24,dtype=torch.float32).reshape(1,1,6,4)
        cache.update(x,x+1,0);cache.update(x,x+1,5)
        record=kv_record(cache)
        self.assertEqual(record['layers'][0]['logical_tokens'],6)
        self.assertLessEqual(cache.layers[0].keys.shape[-2],4)
        self.assertEqual(cache.layers[5].keys.shape[-2],6)
        self.assertGreaterEqual(record['deduplicated_storage_bytes'],record['logical_bytes'])


if __name__=='__main__':unittest.main()
