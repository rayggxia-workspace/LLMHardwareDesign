import unittest
import json
from ledger import Ledger, ffn, attention, qualify, tile_classes, ffn_workload


class ResourceLedgerTests(unittest.TestCase):
    def test_ffn_closed_form_and_same_resources(self):
        for t,h,f,tile in ((1,7,19,6),(9,16,47,8),(32,32,64,16)):
            results = [ffn(t,h,f,tile,s) for s in ("materialized","streaming")]
            for r in results:
                c = r["counts"]
                self.assertEqual(c["macs"], 3*t*h*f)
                self.assertEqual(c["external_bytes"], (2*t*h+3*h*f)*4)
                self.assertEqual(c["engine_transfer_bytes"], 3*t*f*4)
                self.assertEqual(c["matrix_to_vector"], 2*t*f*4)
                self.assertEqual(c["vector_to_matrix"], t*f*4)
            self.assertEqual(results[0]["counts"], results[1]["counts"])

    def test_attention_closed_form(self):
        for q,k,hq,hkv,d,qt,kt in ((1,19,4,2,7,4,6),(9,19,6,2,8,4,6),(16,16,4,1,8,8,8)):
            a,b = [attention(q,k,hq,hkv,d,qt,kt,s) for s in ("materialized","streaming")]
            qtiles=(q+qt-1)//qt
            ktiles=(k+kt-1)//kt
            external=(2*hq*q*d+2*qtiles*hkv*k*d)*4
            for r in (a,b):
                self.assertEqual(r["counts"]["macs"], 2*hq*q*k*d)
                self.assertEqual(r["counts"]["external_bytes"],external)
            self.assertEqual(a["counts"]["engine_transfer_bytes"], 2*hq*q*k*4)
            self.assertEqual(b["counts"]["engine_transfer_bytes"],
                             (2*hq*q*k+hq*q*ktiles*d)*4)

    def test_join_does_not_create_storage_or_free_internal_transfers(self):
        r=ffn(7,16,47,8,"streaming")
        split=qualify(r,8192,2048,10,"split")
        joined=qualify(r,8192,2048,10,"joined")
        self.assertEqual(split["selected_schedule_fits"],joined["selected_schedule_fits"])
        self.assertEqual(split["headroom"],joined["headroom"])
        self.assertEqual(split["cross_block_bytes"],joined["local_interengine_bytes"])
        self.assertEqual(joined["cross_block_bytes"],0)

    def test_capacity_reserve_boundary(self):
        r=ffn(7,16,47,8,"streaming")
        m,v=r["peak_bank_bytes"]["matrix"],r["peak_bank_bytes"]["vector"]
        self.assertTrue(qualify(r,m,v,0,"split")["selected_schedule_fits"])
        self.assertFalse(qualify(r,m,v,1,"split")["selected_schedule_fits"])

    def test_single_tile_no_ffn_memory_advantage_assumed(self):
        a=ffn(1,64,8,8,"materialized")
        b=ffn(1,64,8,8,"streaming")
        self.assertGreaterEqual(b["peak_bank_bytes"]["matrix"],a["peak_bank_bytes"]["matrix"])

    def test_stream_attention_can_cost_more_boundary_bytes(self):
        a=attention(16,65,4,2,16,4,8,"materialized")
        b=attention(16,65,4,2,16,4,8,"streaming")
        self.assertLess(b["peak_total_bytes"],a["peak_total_bytes"])
        self.assertGreater(b["counts"]["engine_transfer_bytes"],a["counts"]["engine_transfer_bytes"])

    def test_invalid_or_unbalanced_events_rejected(self):
        l=Ledger();l.alloc("a","matrix",16)
        with self.assertRaises(ValueError): l.alloc("a","vector",16)
        l.alloc("b","vector",8)
        with self.assertRaises(ValueError): l.copy("a","b")
        with self.assertRaises(ValueError): l.finish()
        with self.assertRaises(ValueError):
            with l.repeat(3): l.alloc("c","matrix",4)

    def test_invalid_shapes_rejected(self):
        with self.assertRaises(ValueError): attention(4,4,5,2,8,2,2,"streaming")
        with self.assertRaises(ValueError): attention(5,4,4,2,8,2,2,"streaming")
        with self.assertRaises(ValueError): tile_classes(5,0)
        with self.assertRaises(ValueError): ffn(4,8,16,4,"mystery")
        self.assertEqual(tile_classes(17,8),[(8,2),(1,1)])

    def test_token_tiling_pays_for_weight_reload(self):
        r=ffn_workload(17,16,47,8,8,"streaming")
        self.assertEqual(r["counts"]["external_bytes"],(2*17*16+3*3*16*47)*4)
        self.assertEqual(r["counts"]["macs"],3*17*16*47)
        self.assertEqual(r["counts"]["engine_transfer_bytes"],3*17*47*4)

    def test_derived_dimensions_bound_to_frozen_official_input(self):
        from run import HERE, validate_model
        models=json.loads((HERE/"model-cases.json").read_text(encoding="utf-8"))["cases"]
        for model in models:
            validate_model(model)
            with self.assertRaises(ValueError): validate_model(dict(model,hidden=model["hidden"]+1))
            if "head_dim" in model:
                with self.assertRaises(ValueError): validate_model(dict(model,head_dim=model["head_dim"]+1))


if __name__ == "__main__":
    unittest.main()
