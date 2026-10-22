import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from capture import _metrics, capture_eager, evaluate, online_attention, source_commit_binding


def temporary_directory():
    parent = Path(os.environ["TEMP"]).resolve()
    if os.name == "nt" and parent.drive.upper() != "D:":
        raise RuntimeError("set process TEMP to the authorized D: task scratch before tests")
    return TemporaryDirectory(dir=parent)


class CaptureTests(unittest.TestCase):
    def test_online_offset_causal_and_tails(self):
        rng = np.random.default_rng(19)
        q, k, v = [rng.normal(size=s).astype(np.float32) for s in ((3, 4), (7, 4), (7, 4))]
        allowed = np.arange(7)[None, :] <= np.arange(4, 7)[:, None]
        mask = np.where(allowed, 0, np.finfo(np.float32).min).astype(np.float32)
        scores = (q @ k.T) * np.float32(0.5) + mask
        P = np.exp(scores - scores.max(axis=1, keepdims=True))
        reference = (P / P.sum(axis=1, keepdims=True)) @ v
        for tile in (1, 2, 4, 8):
            output, states = online_attention(q, k, v, mask, 0.5, tile)
            self.assertTrue(_metrics(output, reference)["pass"])
            self.assertEqual(states[-1]["end"], 7)
        for mutation in ("wrong_O_alpha_half", "reset_O_each_tile"):
            wrong, _ = online_attention(q, k, v, mask, 0.5, 2, mutation=mutation)
            self.assertFalse(_metrics(wrong, reference)["pass"])

    def test_nan_fails_and_invalid_mask_rejected(self):
        a = np.ones((1, 2), dtype=np.float32)
        self.assertFalse(_metrics(a * np.nan, a)["pass"])
        with self.assertRaises(ValueError):
            online_attention(a, a, a, np.full((1, 1), np.nan, dtype=np.float32), 1, 1)

    def test_wrapper_passthrough_and_exception_restoration(self):
        returned = (torch.ones((1, 32, 16, 128)), torch.zeros((1, 16, 32, 32)))
        seen = []
        def eager(module, query, key, value, attention_mask, scaling, dropout=0.0, **kwargs):
            seen.append((query, key, value, attention_mask, scaling, kwargs))
            return returned
        api = SimpleNamespace(eager_attention_forward=eager)
        module = SimpleNamespace(layer_idx=0, training=False)
        q, k, v = torch.ones((1, 16, 32, 128)), torch.ones((1, 8, 32, 128)), torch.ones((1, 8, 32, 128))
        mask = torch.where(torch.arange(32)[None, :] <= torch.arange(32)[:, None], 0., torch.finfo(torch.float32).min)[None, None]
        captures = {}
        with capture_eager(api, {"name": "prefill32"}, captures):
            result = api.eager_attention_forward(module, q, k, v, mask, scaling=0.125, custom="unchanged")
            self.assertIs(result, returned)
        self.assertIs(api.eager_attention_forward, eager)
        self.assertIs(seen[0][0], q)
        self.assertIs(seen[0][3], mask)
        self.assertEqual(seen[0][-1], {"custom": "unchanged"})
        self.assertEqual(captures["prefill32"]["reference"].shape, (32, 128))
        with self.assertRaisesRegex(RuntimeError, "intentional"):
            with capture_eager(api, {}, {}):
                raise RuntimeError("intentional")
        self.assertIs(api.eager_attention_forward, eager)

    def test_result_archive_and_single_tile_negative_scope(self):
        rng = np.random.default_rng(27)
        captures = {}
        for name, qlen, klen in (("prefill32", 32, 32), ("decode48", 1, 48)):
            q, k, v = [rng.normal(size=shape).astype(np.float32) for shape in ((qlen, 8), (klen, 8), (klen, 8))]
            positions = np.arange(klen - qlen, klen)
            mask = np.where(np.arange(klen)[None, :] <= positions[:, None], 0., np.finfo(np.float32).min).astype(np.float32)
            reference, _ = online_attention(q, k, v, mask, 0.25, klen)
            captures[name] = {"query": q, "key": k, "value": v, "reference": reference,
                              "additive_mask": mask, "mask_present": np.array(True),
                              "scaling": np.array(0.25, dtype=np.float32), "query_positions": positions}
        with temporary_directory() as temp:
            result = evaluate(captures, Path(temp))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["positive_passed"], 6)
            self.assertEqual(result["negative_detected"], 10)
            self.assertEqual(result["negative_not_applicable"], 2)
            json.dumps(result, allow_nan=False)
            with np.load(Path(temp) / "attention-stages.npz", allow_pickle=False) as arrays:
                self.assertEqual(arrays["prefill32.tile8.O"].shape, (4, 32, 8))

    def test_source_commit_binding_checks_real_bytes(self):
        with temporary_directory() as temp:
            root = Path(temp).resolve()
            script = root / "capture.py"
            script.write_bytes(b"frozen source\n")
            with patch("capture.subprocess.check_output", return_value=b"frozen source\n") as show:
                self.assertTrue(source_commit_binding(root, script, "abc123")["bytes_match_commit"])
                self.assertEqual(show.call_args.args[0][-1], "abc123:capture.py")
            with patch("capture.subprocess.check_output", return_value=b"other source\n"):
                self.assertFalse(source_commit_binding(root, script, "abc123")["bytes_match_commit"])


if __name__ == "__main__":
    unittest.main()
