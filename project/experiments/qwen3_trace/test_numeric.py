"""Small protocol tests, not a real Qwen run or synthetic attention benchmark."""

import json
from types import SimpleNamespace
import unittest

import torch
from transformers import PretrainedConfig

from numeric import _cache_snapshot, _prefix_integrity, _tensor_metrics, run_numeric


class ProtocolModel(torch.nn.Module):
    """A tiny causal, position-sensitive model exposing real DynamicCache API."""

    def __init__(self, *, corrupt_append=False):
        super().__init__()
        self.config = PretrainedConfig(
            num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=2,
            hidden_size=4, head_dim=2, layer_types=["full_attention"] * 2,
        )
        self.register_buffer("scale", torch.tensor(1.0))
        self.corrupt_append = corrupt_append
        self.eval()

    def forward(self, input_ids, position_ids, past_key_values, **kwargs):
        x = input_ids.float().unsqueeze(1).unsqueeze(-1)
        pos = position_ids.float().unsqueeze(1).unsqueeze(-1)
        head = torch.arange(2).view(1, 2, 1, 1).float()
        column = torch.arange(2).view(1, 1, 1, 2).float()
        for layer in range(2):
            keys = x + pos * (head + 1) + head * 3 + column + layer
            values = x * (head + 1) + pos + column * 2 + layer
            past_key_values.update(keys, values, layer)
            if self.corrupt_append and past_key_values.layers[layer].keys.shape[-2] > input_ids.shape[1]:
                past_key_values.layers[layer].keys[..., 0, 0] += 1
        # A true prefix-dependent reduction with order-sensitive KV-head weights.
        layer = past_key_values.layers[-1]
        weighted = (layer.values * (head + 1)).sum(dim=(1, 3))
        cumsum = weighted.cumsum(dim=-1)[:, -input_ids.shape[1]:]
        last_pos = position_ids.float()
        logits = torch.stack((cumsum, cumsum * 0.5 + last_pos, -cumsum, last_pos - 1), dim=-1)
        return SimpleNamespace(logits=logits[:, -1:, :].float(), past_key_values=past_key_values)


class NumericProtocolTests(unittest.TestCase):
    def test_all_paths_and_controls_and_json(self):
        ids = torch.tensor([[1, 2, 3, 5, 7, 11, 13]], dtype=torch.long)
        result = run_numeric(ProtocolModel(), ids, prefix=4, steps=3)
        self.assertEqual(result["status"], "PASS", result["failures"])
        self.assertEqual(result["totals"]["positive_checks"], 9)
        self.assertEqual(result["totals"]["negative_passed"], 2)
        self.assertEqual([r["prefix_length"] for r in result["positive_paths"]["chunked_prefill"]], [2, 4, 5, 6, 7])
        self.assertEqual(len(result["positive_paths"]["single_prefill"][-1]["comparison"]["cache"]["fields"]), 4)
        json.dumps(result, allow_nan=False)

    def test_failures_are_retained_at_each_affected_step(self):
        result = run_numeric(ProtocolModel(corrupt_append=True), torch.arange(7).view(1, -1), prefix=4, steps=3)
        self.assertEqual(result["status"], "FAIL")
        failed = [r for values in result["positive_paths"].values() for r in values if not r["passed"]]
        self.assertGreaterEqual(len(failed), 6)
        self.assertEqual(len(result["positive_paths"]["single_prefill"]), 4)
        self.assertEqual(len(result["positive_paths"]["chunked_prefill"]), 5)
        self.assertTrue(any(r.get("prefix_integrity", {}).get("unchanged") is False for r in failed))
        json.dumps(result, allow_nan=False)

    def test_hash_detects_signed_zero_without_numeric_difference(self):
        tensor = torch.zeros((1, 2, 2, 2), dtype=torch.float32)
        cache = SimpleNamespace(layers=[SimpleNamespace(keys=tensor, values=tensor.clone())])
        before = _cache_snapshot(cache, 2)
        cache.layers[0].keys[0, 0, 0, 0] = -0.0
        check = _prefix_integrity(before, cache)
        self.assertFalse(check["unchanged"])
        self.assertTrue(torch.equal(cache.layers[0].keys, cache.layers[0].values))

    def test_nan_and_wrong_shape_never_match(self):
        reference = torch.ones(2, dtype=torch.float32)
        self.assertFalse(_tensor_metrics(torch.tensor([float("nan"), 1.0]), reference, 1e-4, 1e-4)["match"])
        self.assertFalse(_tensor_metrics(torch.ones(1), reference, 1e-4, 1e-4)["match"])

    def test_registered_hooks_are_rejected_without_removal(self):
        model = ProtocolModel()
        handle = model.register_forward_hook(lambda *args: None)
        result = run_numeric(model, torch.arange(7).view(1, -1), prefix=4, steps=3)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("hooks", result["failures"][0]["error"])
        self.assertTrue(model._forward_hooks)
        handle.remove()

    def test_invalid_tolerance_is_evidence_not_silent_acceptance(self):
        for tolerance in (-1, float("nan"), float("inf"), True):
            result = run_numeric(ProtocolModel(), torch.arange(7).view(1, -1), prefix=4, steps=3, atol=tolerance)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["failures"][0]["stage"], "setup")
            json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
