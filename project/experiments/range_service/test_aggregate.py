"""Synthetic shard union tests; no real model or schedule execution."""
import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("issue68_aggregate_test", Path(__file__).with_name("aggregate.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def fixture(root, round_number=1):
    task = {"id": "native.evaluation.S32.D31.guard_rescale",
            "precision": {"state_bits": 32, "decay_fraction": 31, "state_unit": [-28, -28]},
            "tokens": [{"attempts": [{"accepted": True, "epoch": 0}]}],
            "commit_contract": "synthetic atomic contract"}
    fingerprint = A.hashlib.sha256(A.canonical(task)).hexdigest()
    source = {"commit": "a" * 40, "service_sha256": "b" * 64}
    for org in A.ORGANIZATIONS:
        shard = root / f"svc-n-{org}-{round_number:02d}"
        shard.mkdir()
        artifacts, rows = {}, []
        for ext in A.GRID["ext_profiles"]:
            for tile in A.GRID["tiles"]:
                for route in A.GRID["norm_routes"]:
                    choices = []
                    for strategy in A.GRID["strategies"]:
                        name = f"task0.{org}.tile{tile}.{route}.ext{ext}.{strategy}.json.gz"
                        witness = {"schema": A.SCHEMA, "task": task, "task_fingerprint": fingerprint,
                                   "config": {"organization": org, "tile": tile, "norm_route": route,
                                              "ext_ii": ext, "strategy": strategy, "state_bits": 32},
                                   "makespan": 10, "nodes": [], "producer_audit": {"status": "PASS"}}
                        (shard / name).write_bytes(gzip.compress(A.canonical(witness), mtime=0))
                        artifacts[name] = A.descriptor(shard / name)
                        choices.append({"strategy": strategy, "cycles": 10, "nodes": 0, "witness": name})
                    rows.append({"task": task["id"], "task_fingerprint": fingerprint,
                                 "state_bits": 32, "commit_contract": task["commit_contract"],
                                 "organization": org, "tile": tile, "norm_route": route, "ext_ii": ext,
                                 "strategies": choices, "best": choices[1]})
        metrics = {"schema": A.SCHEMA, "status": "PASS_CONDITIONAL_SCHEDULE", "source": source,
                   "results": rows, "fairness": "synthetic fixture"}
        (shard / "metrics.json").write_bytes(A.canonical(metrics))
        artifacts["metrics.json"] = A.descriptor(shard / "metrics.json")
        manifest = {"schema": A.SCHEMA, "config": dict(A.GRID, lane_profiles=[org]),
                    "source": source, "input_root": "/same-frozen-issue66", "range_root": "/same-frozen-range",
                    "artifacts": artifacts}
        (shard / "manifest.json").write_bytes(A.canonical(manifest))


def rewrite_shard(root, org, change):
    shard = root / ("svc-n-" + org + "-01")
    manifest = A.load(shard / "manifest.json")
    change(shard, manifest)
    (shard / "manifest.json").write_bytes(A.canonical(manifest))


class AggregateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aggregate-boundary-")
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.binding = {"commit": "c" * 40, "aggregate_sha256": A.sha(A.__file__)}

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_hardlink_union_and_round_repeat(self):
        fixture(self.root, 2)
        a = self.root / "service-native01"
        b = self.root / "service-native02"
        result = A.aggregate(self.root, "native", 1, a, self.binding)
        A.aggregate(self.root, "native", 2, b, self.binding)
        self.assertEqual((result["cases"], result["witnesses"]), (56, 112))
        self.assertEqual((a / "metrics.json").read_bytes(), (b / "metrics.json").read_bytes())
        for name in A.load(a / "manifest.json")["artifacts"]:
            if name.endswith(".gz"):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
                self.assertGreaterEqual((a / name).stat().st_nlink, 2)
        with self.assertRaisesRegex(ValueError, "already exists"):
            A.aggregate(self.root, "native", 1, a, self.binding)

    def test_missing_grid_rejected(self):
        rewrite_shard(self.root, "shared8", lambda _, m: m["config"].update(ext_profiles=[1]))
        with self.assertRaisesRegex(ValueError, "grid"):
            A.validate(self.root, "native", 1)

    def test_mutated_artifact_rejected(self):
        shard = self.root / "svc-n-shared8-01"
        name = next(n for n in A.load(shard / "manifest.json")["artifacts"] if n.endswith(".gz"))
        with (shard / name).open("ab") as f:
            f.write(b"corrupt")
        with self.assertRaisesRegex(ValueError, "SHA/bytes"):
            A.validate(self.root, "native", 1)

    def test_source_or_input_mismatch_rejected(self):
        rewrite_shard(self.root, "split6_2", lambda _, m: m.update(range_root="/wrong-range"))
        with self.assertRaisesRegex(ValueError, "source/input"):
            A.validate(self.root, "native", 1)

    def test_rehashed_wrong_precision_rejected(self):
        def change(shard, manifest):
            name = next(n for n in manifest["artifacts"] if n.endswith(".gz"))
            witness = A.json.loads(gzip.decompress((shard / name).read_bytes()))
            witness["task"]["precision"]["state_bits"] = 16
            (shard / name).write_bytes(gzip.compress(A.canonical(witness), mtime=0))
            manifest["artifacts"][name] = A.descriptor(shard / name)
        rewrite_shard(self.root, "shared8", change)
        with self.assertRaisesRegex(ValueError, "precision"):
            A.validate(self.root, "native", 1)

    def test_rehashed_wrong_best_rejected(self):
        def change(shard, manifest):
            metrics = A.load(shard / "metrics.json")
            metrics["results"][0]["best"] = metrics["results"][0]["strategies"][0]
            (shard / "metrics.json").write_bytes(A.canonical(metrics))
            manifest["artifacts"]["metrics.json"] = A.descriptor(shard / "metrics.json")
        rewrite_shard(self.root, "shared8", change)
        with self.assertRaisesRegex(ValueError, "minimum"):
            A.validate(self.root, "native", 1)

    def test_unsafe_output_and_binding_rejected(self):
        with self.assertRaisesRegex(ValueError, "binding"):
            A.aggregate(self.root, "native", 1, self.root / "service-native01", {})
        with self.assertRaisesRegex(ValueError, "output path"):
            A.aggregate(self.root, "native", 1, self.root / "wrong", self.binding)


if __name__ == "__main__":
    unittest.main()
