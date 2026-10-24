import copy
import tempfile
from pathlib import Path
import unittest

import numpy as np

import audit_io as aio
import receive_reference as receiver


class ReferenceTests(unittest.TestCase):
    def test_stable_and_native_actual_score_ties(self):
        logits = np.zeros((1, 40), np.float64)
        stable = np.arange(8, dtype=np.int64)[None]
        self.assertEqual(receiver.route_summary(logits, stable, True)["exact_cutoff_tie_tokens"], 1)
        other = np.arange(8, 16, dtype=np.int64)[None]
        receiver.route_summary(logits, other, False)
        with self.assertRaisesRegex(ValueError, "stable"):
            receiver.route_summary(logits, other, True)
        duplicate = stable.copy()
        duplicate[0, 1] = duplicate[0, 0]
        with self.assertRaisesRegex(ValueError, "unique"):
            receiver.route_summary(logits, duplicate, False)

    def test_near_tie_is_never_tolerance_merged(self):
        logits = np.zeros((1, 40), np.float64)
        logits[0, 39] = np.nextafter(0.0, 1.0)
        ids = np.array([[39, 0, 1, 2, 3, 4, 5, 6]], np.int64)
        receiver.route_summary(logits, ids, True)
        with self.assertRaisesRegex(ValueError, "stable"):
            receiver.route_summary(logits, np.arange(8, dtype=np.int64)[None], True)

    def test_independent_linear_detects_logit_mutation(self):
        x = np.array([[1, -2, 3], [4, 5, -6]], np.float64)
        w = np.array([[i, 2 * i, -i] for i in range(40)], np.float64)
        logits = x @ w.T
        ids = np.array([sorted(range(40), key=lambda i: (-row[i], i))[:8] for row in logits], np.int64)
        selected = np.take_along_axis(logits, ids, 1)
        e = np.exp(selected - selected.max(axis=1, keepdims=True))
        weights = e / e.sum(axis=1, keepdims=True)
        receiver.verify_router(x, w, logits, ids, weights, "model64")
        bad = logits.copy()
        bad[0, 0] += 1
        with self.assertRaisesRegex(ValueError, "linear"):
            receiver.verify_router(x, w, bad, ids, weights, "model64")
        bad_weight = weights.copy()
        bad_weight[0, 0] += 0.01
        with self.assertRaisesRegex(ValueError, "softmax"):
            receiver.verify_router(x, w, logits, ids, bad_weight, "model64")

    def test_artifact_rewrite_sha_negative_reaches_semantic_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            np.savez(folder / "trace.npz", **{"sample": np.arange(8, dtype=np.int64)[None]})
            aio.save_json(folder / "manifest.json", {
                "kind": "fixture", "status": "EXECUTED", "artifacts": [
                    dict(path="trace.npz", **aio.descriptor(folder / "trace.npz"))]})
            before = aio.descriptor(folder / "trace.npz")
            def corrupt(a):
                a[0, 1] = a[0, 0]
                return a
            receiver.rewrite_npz_member(folder / "trace.npz", "sample", corrupt)
            with self.assertRaisesRegex(ValueError, "hash"):
                aio.verify_manifest(folder)
            aio.replace_artifact_hash(folder, "trace.npz")
            aio.verify_manifest(folder)
            self.assertNotEqual(before, aio.descriptor(folder / "trace.npz"))
            values = receiver.arrays(folder / "trace.npz")["sample"]
            with self.assertRaisesRegex(ValueError, "unique"):
                receiver.route_summary(np.zeros((1, 40)), values, True)

    def test_manifest_duplicate_escape_and_source_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                aio.child(root, "../elsewhere")
            with self.assertRaises(ValueError):
                aio.child(root, "C:/elsewhere")
            (root / "tiny").write_text("a")
            a = dict(path="tiny", **aio.descriptor(root / "tiny"))
            aio.save_json(root / "manifest.json", {"artifacts": [a, a]})
            with self.assertRaisesRegex(ValueError, "duplicate"):
                aio.verify_manifest(root)
            source = root / "source.py"
            source.write_text("# source\n")
            digest = aio.sha(source)
            m = {"source": {"commit": "a" * 40, "field": digest}, "producer_sha256": digest}
            aio.check_source(m, source, "field")
            m["source"]["commit"] = "not-a-commit"
            with self.assertRaisesRegex(ValueError, "commit"):
                aio.check_source(m, source, "field")

    def test_metric_flag_cannot_be_overwritten_by_small_l2(self):
        x = np.ones((2, 2))
        y = x.copy()
        y[0, 0] += 0.01
        result = receiver.metric(y, x)
        self.assertGreater(result["max_abs"], receiver.GATE["max_abs_max"])
        with self.assertRaisesRegex(ValueError, "metric"):
            receiver.equal_metric({"relative_l2": 0, "max_abs": 0}, result)


if __name__ == "__main__":
    unittest.main()
