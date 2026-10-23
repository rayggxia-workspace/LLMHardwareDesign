"""No neural inference: independent known-value and protocol consistency checks."""
import copy
import json
from pathlib import Path
import unittest
from analyze import read_catalog,state_bound,minimum_cover,HERE


class Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=read_catalog();cls.models={m["key"]:m for m in cls.catalog["models"]}
        cls.plan=json.loads((HERE/"plan.json").read_text(encoding="utf-8"))
    def test_all_variants_and_evidence_gaps_explicit(self):
        self.assertEqual(len(self.models),17)
        self.assertEqual(sum("config" in m for m in self.models.values()),12)
        for key in ("gemma4","gemma12","llama3","llama32","llama32-1"):
            self.assertNotIn("config",self.models[key])
            self.assertNotIn("kv_payload_bytes",state_bound(self.models[key],8192))
    def test_gqa_known_values_not_monotonic_with_parameter_count(self):
        self.assertEqual(state_bound(self.models["qwen25"],8192)["kv_payload_bytes"],288*1024**2)
        self.assertEqual(state_bound(self.models["qwen3"],8192)["kv_payload_bytes"],896*1024**2)
        self.assertEqual(state_bound(self.models["phi"],8192)["kv_payload_bytes"],1024**3)
        # Qwen3 head_dim is explicit128, despite H/nQ=64.
        self.assertEqual(state_bound(self.models["qwen3"],1)["head_dim"],128)
    def test_window_field_does_not_enable_qwen_local_attention(self):
        for key in ("qwen2","qwen25","r1distill"):
            a=state_bound(self.models[key],8192);b=state_bound(self.models[key],16384)
            self.assertEqual(a["local_layers"],0)
            self.assertEqual(b["kv_payload_bytes"],2*a["kv_payload_bytes"])
    def test_hybrid_keeps_both_growing_and_fixed_state(self):
        a=state_bound(self.models["qwen35"],1024);b=state_bound(self.models["qwen35"],8192)
        self.assertEqual((a["full_layers"],a["recurrent_layers"]),(8,24))
        self.assertEqual(b["kv_payload_bytes"],256*1024**2)
        self.assertEqual(b["candidate_state_f32_bytes"],48*1024**2)
        self.assertEqual(a["candidate_state_f32_bytes"],b["candidate_state_f32_bytes"])
        self.assertEqual(b["candidate_conv_f16_minimum_history_bytes"],1179648)
        self.assertEqual(b["candidate_conv_f16_kernel_alloc_bytes"],1572864)
    def test_distillation_does_not_preserve_teacher_hardware(self):
        native=state_bound(self.models["r1"],128)
        self.assertEqual((native["expert_count"],native["selected_experts"]),(256,8))
        self.assertNotIn("kv_payload_bytes",native)
        self.assertNotIn("mla",self.models["r1distill"]["features"])
        self.assertNotIn("moe",self.models["r1distill-llama"]["features"])
        self.assertEqual(native["candidate_compressed_elements_per_token_per_layer"],576)
    def test_frozen_feature_cover_and_launch_gate(self):
        cost,n,selected=minimum_cover(self.catalog["models"],self.plan["required_primary_features"])
        self.assertEqual((cost,n,selected),(1,3,("gemma4","qwen25","qwen35")))
        with self.assertRaises(ValueError):minimum_cover([m for m in self.catalog["models"] if "local_global_attention" not in m["features"]],self.plan["required_primary_features"])
        self.assertFalse(self.plan["new_numerical_runs_enabled"])
        self.assertEqual(self.plan["heldout_default"],"phi")
        self.assertNotIn("qwen3-4",self.plan["primary"])
    def test_moe_total_storage_is_not_active_model_size(self):
        m=self.models["qwen3moe"]
        self.assertGreater(m["checkpoint_tensor_elements"]//2,14*1024**3)
        self.assertIn("moe",m["features"])
        self.assertNotIn(m["key"],self.plan["primary"])
    def test_missing_integer_capabilities_not_marked_supported(self):
        self.assertIn("qkv_bias",self.models["qwen25"]["features"])
        self.assertNotIn("qkv_bias",self.models["qwen3"]["features"])
        self.assertGreaterEqual(len(self.plan["integer_capability_gaps_to_close_before_full_model_acceptance"]),5)


if __name__=="__main__":unittest.main(verbosity=2)
