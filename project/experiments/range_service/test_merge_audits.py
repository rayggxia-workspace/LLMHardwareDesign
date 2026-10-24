"""Tiny synthetic receipt graph: provenance/coverage tests, no fake DAG replay."""
import copy
import gzip
import importlib.util
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("parallel_service_merge", Path(__file__).with_name("merge_audits.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(root):
    """Each synthetic 'witness' is a placeholder, never a timing qualification."""
    suite, task = "legacy", m.expected_task("legacy")
    prod_source = dict(commit="a" * 40, service_sha256="b" * 64)
    audit_binding = dict(commit="c" * 40, receive_service_sha256=m.RECEIVER_SHA256)
    (root / "phase9").mkdir()
    m.save(root / "phase9" / "binding.json", audit_binding)
    audit_sha = m.sha(root / "phase9" / "binding.json")
    logical_rows, logical_artifacts, provenance = [], {}, []
    for org in m.ORGANIZATIONS:
        suffix = org.removeprefix("shared").removeprefix("split")
        rows, cases, signatures = [], [], []
        for ext, tile, route in itertools.product([1, 16], [16, 32], ["reread", "spill"]):
            choices = []
            for strategy in ("fifo", "critical"):
                name = f"synthetic.{org}.{ext}.{tile}.{route}.{strategy}.json.gz"
                cycles = 1000 + ext + tile + (100 if route == "spill" else 0) + (10 if strategy == "fifo" else 0)
                choices.append(dict(strategy=strategy, cycles=cycles, witness=name, nodes=4,
                                    memory={"V": 5120, "R": 8192}, payload_bytes=64, wire_bytes=96))
                cases.append(dict(witness=name, id=[task, org, tile, route, ext, strategy], cycles=cycles,
                    independent_lower_bound=cycles - 1, precedence_lower_bound=cycles - 2, operations=4,
                    payload_bytes=64, wire_bytes=96, resident_bytes={"V": 5120, "R": 8192},
                    task_fingerprint="d" * 64, commit_contract="synthetic atomic contract", physical_claim=False))
                if org != "shared8":
                    signatures.append(dict(key=[task, tile, route, ext, strategy, suffix], organizations=[org],
                        signature=dict(cycles=cycles, nodes_sha256="e" * 64, allocations_sha256="f" * 64, inventory_sha256="0" * 64)))
            rows.append(dict(task=task, task_fingerprint="d" * 64, state_bits=32,
                commit_contract="synthetic atomic contract", organization=org, tile=tile, norm_route=route,
                ext_ii=ext, strategies=choices, best=min(choices, key=lambda c: (c["cycles"], c["strategy"]))))
        metrics = dict(schema=m.SCHEMA, status="PASS_CONDITIONAL_SCHEDULE", results=rows, source=prod_source)
        for number in (1, 2):
            shard = root / f"svc-l-{org}-{number:02d}"
            shard.mkdir()
            for case in cases:
                (shard / case["witness"]).write_bytes(gzip.compress(json.dumps(dict(synthetic_placeholder=case["witness"])).encode(), mtime=0))
            m.save(shard / "metrics.json", metrics)
            artifacts = {p.name: m.descriptor(p) for p in shard.iterdir()}
            manifest = dict(schema=m.SCHEMA, config=dict(m.GRID, lane_profiles=[org]), source=prod_source,
                            input_root="synthetic-numeric", range_root="synthetic-range", artifacts=artifacts)
            m.save(shard / "manifest.json", manifest)
        negative = [dict(mutation=x, rewritten_SHA_passed=True, status="REJECTED_INDEPENDENT_SEMANTICS")
                    for x in ("dependency", "overlap", "capacity", "epoch")]
        audit = dict(status="PASS_INDEPENDENT_SERVICE", source=dict(receive_service_sha256=m.RECEIVER_SHA256,
            commit=audit_binding["commit"], binding_sha256=audit_sha),
            two_rounds=dict(all_scientific_SHA_identical=True, artifacts=17, arithmetic_schedules_independent=1),
            declared_strategies=["critical", "fifo"], complete_witnesses=16,
            declared_source_root="synthetic-numeric", range_root="synthetic-range", norm_stage="norm03",
            quality_accepted=False, hardware_implemented=False, shared_split_label_only_pairs=0,
            shared_split_label_only_cycles_difference=None, negative_checks=negative, cases=cases,
            shared_split_signatures=signatures)
        audit_dir = root / f"receive-svc-l-{org}-01"
        audit_dir.mkdir()
        m.save(audit_dir / "audit.json", audit)
        logical_rows.extend(rows)
    for number in (1, 2):
        dest = root / f"service-legacy{number:02d}"
        dest.mkdir()
        artifacts, receipts = {}, []
        for org in m.ORGANIZATIONS:
            shard = root / f"svc-l-{org}-{number:02d}"
            sm = m.load(shard / "manifest.json")
            for name, desc in sm["artifacts"].items():
                if name == "metrics.json":
                    continue
                (dest / name).hardlink_to(shard / name)
                artifacts[name] = desc
            receipts.append(dict(directory=shard.name, manifest=m.descriptor(shard / "manifest.json"),
                                 metrics=sm["artifacts"]["metrics.json"], cases=8, witnesses=16))
        m.save(dest / "metrics.json", dict(schema=m.SCHEMA, status="PASS_CONDITIONAL_SCHEDULE", source=prod_source, results=logical_rows))
        artifacts["metrics.json"] = m.descriptor(dest / "metrics.json")
        m.save(dest / "manifest.json", dict(schema=m.SCHEMA, config=dict(m.GRID, lane_profiles=list(m.ORGANIZATIONS)),
            source=prod_source, input_root="synthetic-numeric", range_root="synthetic-range", artifacts=artifacts,
            aggregation_source=dict(shards=receipts)))
    return dict(commit="1" * 40, merge_audits_sha256=m.sha(Path(m.__file__)))


class MergeAuditTests(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get("TMPDIR") or os.environ.get("TEMP")
        self.tmp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.tmp.name)
        self.binding = fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_merge(self):
        return m.merge(self.root, "legacy", self.root / "merged.json", self.binding)

    def mutate_audit(self, fn):
        p = self.root / "receive-svc-l-shared2_6-01" / "audit.json"
        value = m.load(p)
        fn(value)
        m.save(p, value)

    def test_full_parallel_coverage_and48_pairs(self):
        result = self.run_merge()
        self.assertEqual((result["complete_witnesses"], result["shared_split_label_only_pairs"]), (112, 48))
        self.assertEqual(result["status"], "PASS_INDEPENDENT_SERVICE_SHARD_UNION")
        self.assertEqual(result["source"]["receive_service_sha256"], m.RECEIVER_SHA256)
        self.assertEqual(result["merge_source"]["commit"], self.binding["commit"])
        self.assertNotIn("merge_audits_sha256", result["source"])
        self.assertIn("does not redo", result["replay_scope"])

    def test_stale_receiver_source_rejected(self):
        self.mutate_audit(lambda a: a["source"].update(receive_service_sha256="0" * 64))
        with self.assertRaisesRegex(AssertionError, "frozen independent receiver source"):
            self.run_merge()

    def test_missing_witness_audit_rejected(self):
        self.mutate_audit(lambda a: a["cases"].pop())
        with self.assertRaisesRegex(AssertionError, "complete independent shard witness"):
            self.run_merge()

    def test_changed_metric_rejected(self):
        self.mutate_audit(lambda a: a["cases"][0].update(cycles=a["cases"][0]["cycles"] + 1))
        with self.assertRaisesRegex(AssertionError, "independent audit/logical metric cycles"):
            self.run_merge()

    def test_different_resource_signature_rejected(self):
        self.mutate_audit(lambda a: a["shared_split_signatures"][0]["signature"].update(inventory_sha256="9" * 64))
        with self.assertRaisesRegex(AssertionError, "shared/split exact same-resource"):
            self.run_merge()

    def test_mutated_logical_bytes_rejected(self):
        folder = self.root / "service-legacy01"
        name = next(n for n in m.load(folder / "manifest.json")["artifacts"] if n.endswith(".json.gz"))
        # Break only the logical link, preserving immutable original shard bytes.
        path = folder / name
        path.unlink()
        path.write_bytes(b"changed synthetic bytes")
        with self.assertRaisesRegex(AssertionError, "artifact SHA/bytes"):
            self.run_merge()


if __name__ == "__main__":
    unittest.main()
