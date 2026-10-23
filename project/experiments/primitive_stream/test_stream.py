import json
from pathlib import Path
import unittest
import numpy as np
from cache import ImmutableKV
from run import calibrate,prepare

class StreamContract(unittest.TestCase):
    def setUp(self):
        self.k=np.arange(12,dtype=np.int8).reshape(3,4);self.v=-self.k

    def test_chunking_and_published_prefix(self):
        a=ImmutableKV(4,4,"fixed");b=ImmutableKV(4,4,"fixed")
        a.append([0,1,2],self.k,self.v,0,"fixed")
        for t in range(3):b.append([t],self.k[t:t+1],self.v[t:t+1],t,"fixed")
        for x,y in zip(a.read(3),b.read(3)):self.assertTrue(np.array_equal(x,y))
        self.assertEqual(sum(e["old_payload_rewrite_bytes"] for e in b.events),0)

    def test_reject_stale_read_and_write(self):
        cache=ImmutableKV(4,4,"fixed");cache.append([0],self.k[:1],self.v[:1],0,"fixed")
        with self.assertRaises(ValueError):cache.read(0)
        with self.assertRaises(ValueError):cache.append([1],self.k[:1],self.v[:1],0,"fixed")
        self.assertEqual(cache.length,1)

    def test_reject_changed_scale_without_mutation(self):
        c=ImmutableKV(4,4,"fixed");c.append([0],self.k[:1],self.v[:1],0,"fixed")
        before=c.read(1)
        with self.assertRaises(ValueError):c.append([1],self.k[:1],self.v[:1],1,"new_scale")
        self.assertEqual(c.epoch,1)
        for x,y in zip(before,c.read(1)):self.assertTrue(np.array_equal(x,y))

    def test_order_dtype_capacity_are_atomic(self):
        c=ImmutableKV(2,4,"fixed")
        with self.assertRaises(ValueError):c.append([1],self.k[:1],self.v[:1],0,"fixed")
        with self.assertRaises(ValueError):c.append([0],self.k[:1].astype(np.int16),self.v[:1],0,"fixed")
        with self.assertRaises(OverflowError):c.append([0,1,2],self.k,self.v,0,"fixed")
        self.assertEqual(c.length,0)

    def test_shared_g_preserves_two_head_dots(self):
        rng=np.random.default_rng(13);q=rng.normal(size=(2,8,4));k=rng.normal(size=(8,4))*[1,16,64,2]
        p=calibrate(q,k,k,"calibrated_shared_QK_static_KV");g=np.array(p["g"])
        for head in q:self.assertTrue(np.allclose((head*2.**g)@(k*2.**-g).T,head@k.T))
        wrong_g=g.copy();wrong_g[0]+=2
        self.assertFalse(np.allclose((q[1]*2.**wrong_g)@(k*2.**-g).T,q[1]@k.T))

    def test_future_outlier_does_not_refit_frozen_scale(self):
        q=np.ones((2,4,4));k=np.ones((4,4));v=np.ones_like(k)
        p=calibrate(q,k,v,"direct_static_KV");frozen=json.dumps(p,sort_keys=True)
        _,before,_,_,_=prepare(q,k,v,p)
        extended=np.concatenate([k,1024*k[:1]])
        _,after,_,_,clip=prepare(np.ones((2,5,4)),extended,np.ones((5,4)),p)
        self.assertTrue(np.array_equal(before,after[:4]));self.assertGreater(clip["K"],0)
        self.assertEqual(json.dumps(p,sort_keys=True),frozen)

    def test_current_row_Q_scale_has_no_future_dependency(self):
        q=np.ones((2,4,4));k=np.ones((4,4));p=calibrate(q,k,k,"direct_static_KV")
        a,_,_,exps,_=prepare(q,k,k,p)
        q[:,3]*=1024
        b,_,_,new,_=prepare(q,k,k,p)
        self.assertTrue(np.array_equal(a[:,:3],b[:,:3]));self.assertEqual([x[:3] for x in exps],[x[:3] for x in new])

    def test_frozen_text_partitions_are_distinct(self):
        cfg=json.loads(Path(__file__).with_name("experiment.json").read_text())
        self.assertEqual(len(set([cfg["calibration_text"],*cfg["evaluation_texts"].values()])),3)
        self.assertEqual(cfg["query_heads"],[0,1]);self.assertEqual(cfg["kv_head"],0)

if __name__=="__main__":unittest.main(verbosity=2)
