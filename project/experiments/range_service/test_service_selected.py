"""Small source-authority and real rehashed-epoch boundary tests."""
import gzip
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

sp = importlib.util.spec_from_file_location("issue68_service_selected_test", Path(__file__).with_name("service_selected.py"))
M = importlib.util.module_from_spec(sp)
sp.loader.exec_module(M)


class SelectedTest(unittest.TestCase):
    def test_unsafe_path_and_bad_SHA_rejected(self):
        with tempfile.TemporaryDirectory(prefix="service-selected-") as d:
            base = Path(d)
            with self.assertRaisesRegex(ValueError, "unsafe"):
                M.safe(base, "../escape")
            (base / "bytes.bin").write_bytes(b"actual immutable bytes")
            with self.assertRaisesRegex(ValueError, "SHA/bytes"):
                M.checked(base, "bytes.bin", {"bytes": 22, "sha256": "0" * 64})

    def test_producer_success_is_not_independent_authority(self):
        manifest = {"schema": "issue68-service/1", "source": {"service_sha256": M.SERVICE_SHA},
                    "artifacts": {str(i): {} for i in range(113)}}
        metrics = {"source": manifest["source"], "status": "PASS_CONDITIONAL_SCHEDULE", "results": [{}] * 56}
        audit = {"status": "PASS_CONDITIONAL_SCHEDULE", "source": {"receive_service_sha256": M.RECEIVER_SHA},
                 "complete_witnesses": 112, "cases": [{}] * 112, "quality_accepted": False, "hardware_implemented": False}
        with self.assertRaisesRegex(ValueError, "independent receiver authority"):
            M.authority(manifest, metrics, audit)
        audit["status"] = "PASS_INDEPENDENT_SERVICE_SHARD_UNION"
        M.authority(manifest, metrics, audit)
        audit["quality_accepted"] = True
        with self.assertRaisesRegex(ValueError, "quality/hardware"):
            M.authority(manifest, metrics, audit)

    def test_actual_rehashed_epoch_rejected(self):
        receiver_path = Path(os.environ.get("ISSUE68_RECEIVER_PATH", Path(__file__).with_name("receive_service.py")))
        if not receiver_path.is_file():
            self.skipTest("frozen independent receiver not in this isolated worktree")
        receiver = M.receiver_module(receiver_path)
        p = Path(__file__).with_name("service.py")
        spec = importlib.util.spec_from_file_location("selected_synthetic_builder", p)
        source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source)
        task = {"id": "synthetic", "norm_rows": 1, "tokens": [{"attempts": [{"accepted": True, "epoch": 0}]}],
                "precision": {"state_bits": 32, "decay_fraction": 31},
                "commit_contract": "synthetic full-group atomic contract", "numeric_quality_accepted": False}
        witness = source.schedule(source.graph(task, source.config("shared4_4", 16, strategy="critical")))
        witness["task"] = task
        witness["task_fingerprint"] = source.hashlib.sha256(source.canonical(task)).hexdigest()
        witness["producer_audit"] = source.audit(witness)
        self.assertEqual(receiver.verify_witness(witness)["status"], "PASS_INDEPENDENT_SERVICE_WITNESS")
        with tempfile.TemporaryDirectory(prefix="service-selected-epoch-") as d:
            base = Path(d)
            name = "actual-synthetic.json.gz"
            (base / name).write_bytes(gzip.compress(M.canonical(witness), mtime=0))
            result = receiver.actual_negative(base, name, base / "negative", "epoch")
            self.assertEqual(result["status"], "REJECTED_INDEPENDENT_SEMANTICS")
            self.assertTrue(result["rewritten_SHA_passed"])
            self.assertIn("causal task unit/epoch transition", result["error"])


if __name__ == "__main__":
    unittest.main()
