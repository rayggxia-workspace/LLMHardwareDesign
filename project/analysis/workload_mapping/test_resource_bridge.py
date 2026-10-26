"""Chat-recovered checks plus pending hardening; not compared with server files."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

try:
    from . import resource_bridge as bridge
except ImportError:
    import resource_bridge as bridge


def transfer(identifier="data", path=None, shape=None, logical_bits=8,
             storage_bits=8, metadata_bytes=0, messages=1):
    return {"id": identifier, "path": ["source", "sink"] if path is None else path,
            "shape": [64] if shape is None else shape, "logical_bits": logical_bits,
            "storage_bits": storage_bits, "metadata_bytes": metadata_bytes, "messages": messages}


class ResourceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream, cls.candidate, cls.provenance = bridge.load_upstream()
        cls.example = cls.upstream.read_json(bridge.SOURCE_DIR / "examples/qwen3_06b.json")
        cls.tmp_root = Path(os.environ.get("TMPDIR", bridge.HERE.parents[2] / "runs" / "tmp"))
        cls.tmp_root.mkdir(parents=True, exist_ok=True)

    def isolated_sources(self, tmp):
        copied = Path(tmp) / "sources"
        for path in bridge.SOURCE_HASHES:
            target = copied / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bridge.SOURCE_DIR / path, target)
        lock = Path(tmp) / "source_lock.json"
        shutil.copy2(bridge.SOURCE_LOCK, lock)
        return copied, lock

    def test_all_four_sources_verified_without_changing_original_bytes(self):
        result = bridge.verify_sources()
        self.assertTrue(result["source_sha256_verified"])
        self.assertEqual(len(result["files"]), 4)
        self.assertEqual(result["candidate_original"]["commit"],
                         "3fa0b45070c7ce4587240589d48703d02a1b5246")

    def test_packet_known_boundaries(self):
        # Each 64B header is separate. The second packet needs a 64B payload
        # slot even if only one actual byte remains.
        for payload, packets, wire, cycles in (
                (64, 1, 128, 8), (256, 1, 320, 20),
                (1984, 1, 2048, 128), (1985, 2, 2176, 136)):
            with self.subTest(payload=payload):
                item = bridge.account([transfer(shape=[payload])])["transfers"][0]
                self.assertEqual((item["payload_bytes"], item["packets"],
                                  item["wire_bytes"], item["ideal_link_cycles"]),
                                 (payload, packets, wire, cycles))

    def test_i33_i64_metadata_and_three_repeated_two_hop_messages(self):
        # 64*8+5=517 stored bytes; aligned payload576+header64=640 per hop.
        result = bridge.account([transfer(path=["alpha", "beta", "gamma"], shape=[4, 16],
                                          logical_bits=33, storage_bits=64,
                                          metadata_bytes=5, messages=3)])
        item = result["transfers"][0]
        self.assertEqual(item["payload_bytes"], 517)
        self.assertEqual(item["logical_payload_bits"], 2112)
        self.assertEqual(item["storage_container_bytes"], 512)
        self.assertEqual(item["metadata_bytes"], 5)
        self.assertEqual(item["packet_header_and_alignment_bytes"], 123)
        self.assertEqual(item["wire_bytes"], 640)
        self.assertEqual(item["ideal_link_cycles"], 40)
        self.assertEqual(item["hop_summed_wire_bytes_per_step"], 3840)
        self.assertEqual([e["accounted_wire_bytes_per_step"] for e in result["edges"]], [1920, 1920])
        self.assertEqual(result["shared_TX"]["beta"]["accounted_wire_bytes_per_step"], 1920)

    def test_multiple_consumers_share_tx_without_implied_broadcast_or_bandwidth(self):
        records = [transfer("one", ["producer", "one"], [256], 32, 32, messages=200000),
                   transfer("two", ["producer", "two"], [256], 32, 32, messages=200000)]
        result = bridge.account(records)
        self.assertEqual(result["shared_TX"]["producer"]["accounted_wire_bytes_per_step"], 435200000)
        self.assertEqual(len(result["edges"]), 2)
        for entry in result["edges"] + list(result["shared_TX"].values()):
            self.assertIsNone(entry["required_bytes_per_second"])
            self.assertIsNone(entry["capacity_bytes_per_second"])
            self.assertIsNone(entry["lower_bound_exceeds_capacity"])

    def test_arbitrary_names_are_injective_and_not_candidate_instances(self):
        records = [transfer("first", ["M", "S0"]), transfer("second", ["M0", "S01"]),
                   transfer("third", ["S0", "M0"])]
        result = bridge.account(records)
        self.assertEqual({(e["source"], e["destination"]) for e in result["edges"]},
                         {("M", "S0"), ("M0", "S01"), ("S0", "M0")})
        self.assertEqual(set(result["shared_TX"]), {"M", "M0", "S0"})
        self.assertIsNone(result["resource_input"])
        self.assertIn("arithmetic only", result["provenance"]["generic_projection"])

    def test_unknown_message_count_keeps_single_message_and_no_zero_claim(self):
        result = bridge.account([transfer(messages=None)])
        self.assertEqual(result["transfers"][0]["wire_bytes"], 128)
        self.assertIsNone(result["transfers"][0]["hop_summed_wire_bytes_per_step"])
        self.assertEqual(len(result["edges"]), 1)
        self.assertIsNone(result["edges"][0]["accounted_wire_bytes_per_step"])
        self.assertEqual(result["edges"][0]["known_wire_bytes_per_step_lower_bound"], 0)
        self.assertFalse(result["edges"][0]["all_message_counts_known"])
        self.assertIsNone(result["shared_TX"]["source"]["accounted_wire_bytes_per_step"])
        self.assertFalse(result["all_listed_message_counts_known"])
        self.assertTrue(any("unknown message counts" in v for v in result["unresolved"]))

    def test_unknown_count_marks_only_affected_edges_and_shared_tx_incomplete(self):
        records = [transfer("known", ["source", "middle", "sink"], messages=2),
                   transfer("unknown", ["source", "middle", "other"], messages=None)]
        result = bridge.account(records)
        entries = {(e["source"], e["destination"]): e for e in result["edges"]}
        self.assertIsNone(entries[("source", "middle")]["accounted_wire_bytes_per_step"])
        self.assertEqual(entries[("source", "middle")]["known_wire_bytes_per_step_lower_bound"], 256)
        self.assertEqual(entries[("middle", "sink")]["accounted_wire_bytes_per_step"], 256)
        self.assertTrue(entries[("middle", "sink")]["all_message_counts_known"])
        self.assertIsNone(entries[("middle", "other")]["accounted_wire_bytes_per_step"])
        self.assertIsNone(result["shared_TX"]["middle"]["accounted_wire_bytes_per_step"])
        self.assertEqual(result["shared_TX"]["middle"]["known_wire_bytes_per_step_lower_bound"], 256)

    def test_supplied_stale_transfer_list_cannot_leak_into_projection(self):
        envelope = copy.deepcopy(self.example)
        envelope["transfers"] = [{
            "name": "stale-must-disappear", "path": ["M", "V"], "shape": [9000],
            "logical_bits": 8, "storage_bits": 8, "metadata_bytes": 0, "messages_per_step": 999,
        }]
        result = bridge.account([transfer("fresh", ["M", "V"])], envelope)
        self.assertEqual([t["name"] for t in result["resource_input"]["transfers"]], ["fresh"])
        self.assertEqual(result["resource_report"]["reference_transport"]["shared_TX"]["M"]
                         ["accounted_wire_bytes_per_step"], 128)
        self.assertEqual(envelope["transfers"][0]["name"], "stale-must-disappear")

    def test_original_s_names_and_renamed_s_names_never_collide(self):
        pairs = [("S0", "S1"), ("M", "S0"), ("S00", "S0"), ("S999", "M")]
        records = [transfer(str(i), list(pair)) for i, pair in enumerate(pairs)]
        result = bridge.account(records)
        self.assertEqual({(e["source"], e["destination"]) for e in result["edges"]}, set(pairs))
        self.assertEqual(set(result["shared_TX"]), {"S0", "M", "S00", "S999"})

    def test_metadata_unknown_is_rejected_from_known_ledger(self):
        with self.assertRaisesRegex(bridge.ResourceError, "metadata_bytes"):
            bridge.account([transfer(metadata_bytes=None)])

    def test_strict_transfer_fields_and_types(self):
        missing = transfer()
        del missing["shape"]
        unknown = transfer()
        unknown["bytez"] = 1
        wrong = [missing, unknown, transfer(shape=[]), transfer(shape=[0]), transfer(shape=[-1]),
                 transfer(shape=[True]), transfer(shape=["N"]), transfer(messages=0),
                 transfer(messages=True), transfer(logical_bits=33, storage_bits=32),
                 transfer(logical_bits=16, storage_bits=8), transfer(storage_bits=24),
                 transfer(metadata_bytes=-1), transfer(path=["only"])]
        for item in wrong:
            with self.subTest(item=item), self.assertRaises(bridge.ResourceError):
                bridge.account([item])
        with self.assertRaisesRegex(bridge.ResourceError, "unique"):
            bridge.account([transfer(), transfer()])

    def test_explicit_resource_envelope_auto_export_equals_independent_manual(self):
        result = bridge.account([transfer("wide", ["M", "V", "R"], [4, 16], 33, 64, messages=3)], self.example)
        manual = copy.deepcopy(self.example)
        manual["hardware"]["candidate_file"] = "profiles/block_candidate_v1.json"
        manual["transfers"] = [{
            "name": "wide", "path": ["M", "V", "R"], "shape": [4, 16],
            "logical_bits": 33, "storage_bits": 64, "metadata_bytes": 0, "messages_per_step": 3,
        }]
        self.assertEqual(result["resource_input"], manual)
        self.assertEqual(result["resource_report"], self.upstream.compute(manual, self.candidate))
        self.assertEqual(result["transfers"][0]["hop_summed_wire_bytes_per_step"], 3456)
        self.assertEqual(result["resource_report"]["transfers"][0]["payload_bytes"], 512)
        self.assertEqual(result["incompatibilities"], [])
        self.assertEqual(result["resource_report"]["model"]["total_parameters"], 596049920)
        self.assertIsNone(result["resource_report"]["scenario"]["target_step_seconds"])

    def test_nonrepresentable_paths_are_reported_and_never_silently_exported(self):
        records = [transfer("legal", ["M", "V"]), transfer("missing-edge", ["M", "R"]),
                   transfer("new-instance", ["M2", "V"])]
        result = bridge.account(records, self.example)
        self.assertEqual(len(result["transfers"]), 3)
        self.assertEqual([t["name"] for t in result["resource_input"]["transfers"]], ["legal"])
        self.assertEqual({i["transfer_id"] for i in result["incompatibilities"]},
                         {"missing-edge", "new-instance"})
        self.assertFalse(result["resource_report"]["reference_transport"]["complete_model_transfer_schedule"])

    def test_unknown_envelope_values_preserved_and_parameters_not_counted_per_message(self):
        original = copy.deepcopy(self.example)
        result = bridge.account([transfer("repeat", ["M", "V"], messages=17)], self.example)
        self.assertEqual(self.example, original)
        self.assertEqual(result["resource_input"]["model"]["total_parameters"], 596049920)
        self.assertIsNone(result["resource_input"]["hardware"]["clock_hz"])
        self.assertIsNone(result["resource_input"]["accounting"]["weight_padding_bytes"])
        self.assertIsNone(result["resource_input"]["precision"]["quantization_contract"])

    def test_resource_limit_precision_unknown_field_and_version_preserved(self):
        mutations = [lambda x: x["model"].update(total_parameters=4000000001),
                     lambda x: x["precision"].update(weight_bits=4),
                     lambda x: x.update(schema_version="llm-resource-input/99"),
                     lambda x: x["scenario"].update(time_budget_seconds=1)]
        for mutate in mutations:
            item = copy.deepcopy(self.example)
            mutate(item)
            with self.subTest(mutate=mutate), self.assertRaises(bridge.ResourceError):
                bridge.account([], item)

    def test_packet_override_does_not_modify_sources_or_claim_original_contract(self):
        records = [transfer("legal", ["M", "V"])]
        first = bridge.account(records)
        changed = bridge.account(records, self.example, packet_profile={"packet_header_bytes": 0})
        self.assertEqual(first["transfers"][0]["wire_bytes"], 128)
        self.assertEqual(changed["transfers"][0]["wire_bytes"], 64)
        self.assertEqual(first, bridge.account(records))
        self.assertIsNone(changed["resource_input"])
        self.assertIsNone(changed["resource_report"])
        self.assertEqual(changed["provenance"]["packet_profile_evidence"], "assumed override")
        self.assertTrue(any("packet_profile differs" in v["reason"] for v in changed["incompatibilities"]))

    def test_invalid_packet_override_rejected(self):
        for override in ({"bandwidth": 999}, {"data_link_bits": 7}, {"beat_bytes": 0},
                         {"endpoint_fifo_bytes": 64}, {"packet_header_bytes": True}):
            with self.subTest(override=override), self.assertRaises(bridge.ResourceError):
                bridge.account([transfer()], packet_profile=override)

    def test_empty_and_deterministic_ledgers(self):
        first = bridge.account([])
        self.assertEqual(first["transfers"], [])
        self.assertEqual(first["edges"], [])
        self.assertEqual(first["shared_TX"], {})
        self.assertEqual(json.dumps(first, sort_keys=True, allow_nan=False),
                         json.dumps(bridge.account([]), sort_keys=True, allow_nan=False))

    def test_source_tamper_detected_in_isolated_copy(self):
        with tempfile.TemporaryDirectory(prefix="resource-", dir=self.tmp_root) as tmp:
            copied, lock = self.isolated_sources(tmp)
            (copied / "estimate.py").write_bytes((copied / "estimate.py").read_bytes() + b"\n")
            with self.assertRaisesRegex(bridge.ResourceError, "SHA-256 mismatch"):
                bridge.verify_sources(copied, lock)

    def test_lock_tamper_detected_in_isolated_copy(self):
        with tempfile.TemporaryDirectory(prefix="resource-", dir=self.tmp_root) as tmp:
            copied, lock = self.isolated_sources(tmp)
            data = json.loads(lock.read_text())
            data["files"][0]["commit"] = "0" * 40
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(bridge.ResourceError, "differs"):
                bridge.verify_sources(copied, lock)

    def test_source_and_lock_changed_together_are_not_trusted(self):
        with tempfile.TemporaryDirectory(prefix="resource-", dir=self.tmp_root) as tmp:
            copied, lock = self.isolated_sources(tmp)
            altered = (copied / "estimate.py").read_bytes() + b"\n# locally modified\n"
            (copied / "estimate.py").write_bytes(altered)
            data = json.loads(lock.read_text())
            for item in data["files"]:
                if item["path"] == "estimate.py":
                    item["sha256"] = hashlib.sha256(altered).hexdigest()
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(bridge.ResourceError, "differs"):
                bridge.verify_sources(copied, lock)

    def test_missing_dependency_is_a_resource_error(self):
        with tempfile.TemporaryDirectory(prefix="resource-", dir=self.tmp_root) as tmp:
            copied = Path(tmp) / "sources"
            copied.mkdir()
            lock = Path(tmp) / "source_lock.json"
            shutil.copy2(bridge.SOURCE_LOCK, lock)
            with self.assertRaisesRegex(bridge.ResourceError, "unavailable"):
                bridge.verify_sources(copied, lock)

    def test_upstream_duplicate_json_key_check_is_retained(self):
        with tempfile.TemporaryDirectory(prefix="resource-", dir=self.tmp_root) as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
            with self.assertRaisesRegex(self.upstream.InputError, "duplicate JSON key"):
                self.upstream.read_json(path)


if __name__ == "__main__":
    unittest.main()
