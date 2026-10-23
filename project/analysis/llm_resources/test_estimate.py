"""Independent known-value, failure and CLI checks; no model/RTL/EDA jobs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import estimate as e

HERE = Path(__file__).resolve().parent


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.config = e.read_json(HERE / "examples/dense_4b.json")
        self.candidate = e.read_json(HERE / "profiles/block_candidate_v1.json")

    def report(self):
        return e.compute(self.config, self.candidate)

    def test_exact_four_billion_boundary_and_known_budget(self):
        r = self.report()
        self.assertEqual(r["storage"]["int8_weight_payload_bytes"], 4_000_000_000)
        self.assertEqual(r["storage"]["weight_scale_bytes"], 125_000_000)
        self.assertEqual(r["matrix_instances_linear_lower_bound"], 2)
        self.assertEqual(r["external"]["required_bytes_per_second_lower_bound"], 41_250_000_000)
        self.assertIn("accounted_external_traffic_exceeds_effective_bandwidth",
                      r["known_constraint_violations_under_input_assumptions"])
        self.assertEqual([s["linear_target_violated"] for s in r["scans"]], [True, False, False])
        self.assertIn("no full-model feasibility certificate", r["status"])

    def test_total_over_four_billion_even_when_active_is_small(self):
        self.config["model"].update(total_parameters=4_000_000_001,
                                    int8_parameters=4_000_000_001,
                                    kind="moe", linear_macs_per_token=500_000_000)
        with self.assertRaises(e.InputError):
            self.report()

    def test_candidate_known_inventory_not_shared_pool(self):
        r = self.report()
        first, second, fourth = [x["inventory"] for x in r["scans"]]
        self.assertEqual(first["all_declared_memory_bytes"], 464 * 1024)
        self.assertEqual(first["signed8_multipliers_including_RQ"], 281)
        self.assertEqual(first["fifo_count"], 30)
        self.assertEqual(first["shared_bank_bytes"], 256 * 1024)
        self.assertEqual(second["all_declared_memory_bytes"], 502 * 1024)
        self.assertEqual(fourth["all_declared_memory_bytes"], 578 * 1024)
        self.assertEqual(r["storage"]["matrix_tile_accounted_bytes"], 16 * 1024)
        self.assertEqual(first["block_instances"], 13)

    def test_unknown_is_null_and_not_zero_or_pass(self):
        self.config = e.read_json(HERE / "examples/unknowns.json")
        r = self.report()
        self.assertIsNone(r["matrix_instances_linear_lower_bound"])
        self.assertIsNone(r["external"]["required_bytes_per_second_lower_bound"])
        self.assertIsNone(r["storage"]["weight_scale_bytes"])
        self.assertTrue(all(x["linear_target_violated"] is None for x in r["scans"]))
        self.assertIn("placement.weights", r["unresolved"])
        self.assertGreater(len(r["unresolved"]), 5)

    def test_illegal_precision_bool_and_unknown_field_rejected(self):
        for section, key, value in [
            ("precision", "weight_bits", 4), ("precision", "accumulator_bits", 16),
            ("scenario", "batch", True), ("hardware", "matrix_utilization", 0),
            ("hardware", "matrix_utilization", 1.1), ("hardware", "matrix_counts", [1, 1]),
            ("hardware", "clock_hz", float("nan")), ("model", "total_parameters", 4e9),
        ]:
            with self.subTest(section=section, key=key, value=value):
                c = copy.deepcopy(self.config)
                c[section][key] = value
                with self.assertRaises(e.InputError):
                    e.compute(c, self.candidate)
        self.config["hardware"]["clock_Hz"] = 100
        with self.assertRaises(e.InputError):
            self.report()

    def test_parameter_partition_and_active_count_consistency(self):
        self.config["model"]["int8_parameters"] -= 1
        with self.assertRaises(e.InputError):
            self.report()
        self.config = e.read_json(HERE / "examples/qwen3_06b.json")
        self.config["model"]["linear_ops"][0]["active_instances"] = 29
        with self.assertRaises(e.InputError):
            self.report()

    def test_modes_mutually_exclusive_and_shape_budget_checked(self):
        self.config["model"]["linear_ops"] = [{
            "name": "bad", "instances": 1, "active_instances": 1,
            "input_features": 100_000, "output_features": 100_000, "prefill_rows": "all"}]
        with self.assertRaises(e.InputError):
            self.report()
        self.config["model"]["linear_macs_per_token"] = None
        with self.assertRaises(e.InputError):
            self.report()

    def test_qwen_config_derived_known_counts_and_kv(self):
        self.config = e.read_json(HERE / "examples/qwen3_06b.json")
        r = self.report()
        self.assertEqual(r["model"]["total_parameters"], 596_049_920)
        self.assertEqual(r["storage"]["int8_weight_payload_bytes"], 595_984_384)
        self.assertEqual(r["storage"]["auxiliary_parameter_accounted_bytes"], 262_144)
        self.assertEqual(r["storage"]["kv_payload_bytes"], 9_175_040)
        self.assertEqual(r["storage"]["kv_scale_accounted_bytes"], 286_720)
        self.assertEqual(r["work"]["linear_MACs_per_step"], 595_984_384)
        self.assertEqual(r["work"]["attention_logical_MACs_per_step"], 18_235_392)
        self.assertEqual(r["scenario"]["decode_evaluated_context_tokens"], 159)

    def test_prefill_lm_head_only_last_row(self):
        self.config = e.read_json(HERE / "examples/qwen3_06b.json")
        self.config["scenario"]["phase"] = "prefill"
        r = self.report()
        self.assertEqual(r["work"]["linear_MACs_per_step"], 440_401_920 * 128 + 155_582_464)
        self.assertNotEqual(r["work"]["linear_MACs_per_step"], 595_984_384 * 128)

    def test_prefill_causal_pairs_with_cached_prefix_and_window(self):
        self.config["model"]["attention"] = [{
            "name": "toy", "layers": 2, "query_heads": 4, "kv_heads": 2,
            "head_dim": 8, "window_tokens": None}]
        self.config["scenario"].update(phase="prefill", cached_tokens=3, input_tokens=2, output_tokens=2)
        self.assertEqual(self.report()["work"]["attention_logical_MACs_per_step"], 1152)
        self.assertEqual(self.report()["storage"]["kv_payload_bytes"], 448)
        self.config["model"]["attention"][0]["window_tokens"] = 3
        r = self.report()
        self.assertEqual(r["work"]["attention_logical_MACs_per_step"], 768)
        self.assertEqual(r["storage"]["kv_payload_bytes"], 192)

    def test_invalid_heads_context_and_decode_horizon(self):
        self.config = e.read_json(HERE / "examples/qwen3_06b.json")
        self.config["model"]["attention"][0]["query_heads"] = 15
        with self.assertRaises(e.InputError):
            self.report()
        self.config = e.read_json(HERE / "examples/qwen3_06b.json")
        self.config["model"]["max_context_tokens"] = 128
        with self.assertRaises(e.InputError):
            self.report()
        self.config["model"]["max_context_tokens"] = None
        self.config["scenario"]["output_tokens"] = 1
        with self.assertRaises(e.InputError):
            self.report()

    def test_batch_rate_is_aggregate_and_weight_reuse_is_explicit(self):
        self.config["scenario"]["batch"] = 2
        r = self.report()
        self.assertEqual(r["scenario"]["target_step_seconds"], 0.2)
        self.assertEqual(r["work"]["linear_MACs_per_step"], 8_000_000_000)
        self.assertEqual(r["matrix_instances_linear_lower_bound"], 2)
        self.assertEqual(r["external"]["required_bytes_per_second_lower_bound"], 20_625_000_000)

    def test_moe_total_storage_active_work_and_unknown_transfers(self):
        self.config = e.read_json(HERE / "examples/moe_2b.json")
        r = self.report()
        self.assertEqual(r["storage"]["int8_weight_payload_bytes"], 2_000_000_000)
        self.assertEqual(r["work"]["linear_MACs_per_step"], 500_000_000)
        self.assertIsNone(r["external"]["linear_weight_accounted_bytes_per_step"])
        self.config["accounting"]["weight_read_passes"] = 1
        self.assertEqual(self.report()["external"]["linear_weight_accounted_bytes_per_step"], 515_625_000)

    def test_recurrence_cold_traffic_requires_policy(self):
        self.config = e.read_json(HERE / "examples/moe_2b.json")
        self.config["scenario"].update(batch=2, phase="prefill", input_tokens=4)
        r = self.report()
        self.assertEqual(r["storage"]["recurrent_bytes"], 8448)
        self.assertIsNone(r["external"]["recurrent_accounted_bytes_per_step"])
        self.config["accounting"]["recurrent_read_write_passes"] = 1
        self.assertEqual(self.report()["external"]["recurrent_accounted_bytes_per_step"], 67_584)

    def test_shared_capacity_does_not_borrow_private_or_fifo(self):
        self.config["placement"]["weights"] = "shared"
        r = self.report()
        self.assertIn("shared_backing_accounted_bytes_exceed_capacity",
                      r["known_constraint_violations_under_input_assumptions"])
        self.config["hardware"]["shared_reserve_bytes"] = 262145
        with self.assertRaises(e.InputError):
            self.report()

    def test_external_capacity_includes_scales(self):
        self.config["hardware"]["external_capacity_bytes"] = 4_000_000_000
        self.assertIn("external_backing_accounted_bytes_exceed_capacity",
                      self.report()["known_constraint_violations_under_input_assumptions"])

    def test_tile_ram_overflow(self):
        self.config["mapping"]["matrix_tile"]["reduction"] = 8192
        self.assertIn("matrix_tile_accounted_bytes_exceed_private_RAM",
                      self.report()["known_constraint_violations_under_input_assumptions"])

    def test_packet_rounding_segmentation_and_per_message_cycles(self):
        for payload, packets, wire, cycles in [
            (64, 1, 128, 8), (256, 1, 320, 20),
            (1984, 1, 2048, 128), (1985, 2, 2176, 136)]:
            with self.subTest(payload=payload):
                r = e.packet(payload, self.candidate)
                self.assertEqual((r["packets"], r["wire_bytes"], r["ideal_link_cycles"]),
                                 (packets, wire, cycles))

    def test_transfer_charges_each_hop_and_i33_container(self):
        t = self.config["transfers"][0]
        t.update(path=["M", "V", "R"], messages_per_step=3, logical_bits=33, storage_bits=64)
        r = self.report()["transfers"][0]
        self.assertEqual(r["payload_bytes"], 512)
        self.assertEqual(r["hop_summed_wire_bytes_per_step"], 3456)
        t["storage_bits"] = 32
        with self.assertRaises(e.InputError):
            self.report()

    def test_absent_edge_rejected(self):
        self.config["transfers"][0]["path"] = ["M", "R"]
        with self.assertRaises(e.InputError):
            self.report()

    def test_rq_is_separate_and_not_free(self):
        self.config["model"]["linear_outputs_per_token"] = 1_000_000
        self.config["hardware"]["rq_initiation_interval_cycles"] = 28
        r = self.report()
        self.assertEqual(r["scans"][0]["RQ_steady_service_cycles_proxy"], 28_000_000)
        self.assertTrue(r["scans"][0]["RQ_target_violated_under_II_assumption"])

    def test_custom_candidate_changes_inventory_and_peak(self):
        self.candidate["blocks"][0]["native_mul8"] = 128
        self.assertEqual(self.report()["matrix_instances_linear_lower_bound"], 3)
        self.assertEqual(self.report()["scans"][0]["inventory"]["signed8_multipliers_including_RQ"], 153)

    def test_invalid_candidate_rejected_without_python_traceback(self):
        with self.assertRaises(e.InputError):
            e.compute(self.config, [])
        for change in ("blocks", "data_link_bits", "endpoint_fifo_bytes"):
            candidate = copy.deepcopy(self.candidate)
            candidate[change] = [3] if change == "blocks" else 3
            with self.subTest(change=change), self.assertRaises(e.InputError):
                e.compute(self.config, candidate)

    def test_compute_is_pure_and_deterministic(self):
        before = copy.deepcopy(self.config)
        self.assertEqual(self.report(), self.report())
        self.assertEqual(before, self.config)

    def test_snapshot_byte_identity(self):
        raw = (HERE / "profiles/block_candidate_v1.json").read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual(actual, e.PROFILE_BLOB)


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(HERE / "estimate.py"), *map(str, args)],
                              capture_output=True, encoding="utf-8", cwd=HERE)

    def test_all_examples_and_deterministic_cli(self):
        for path in sorted((HERE / "examples").glob("*.json")):
            with self.subTest(path=path.name):
                first, second = self.run_cli(path), self.run_cli(path)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(first.stdout, second.stdout)
                report = json.loads(first.stdout)
                self.assertTrue(report["provenance"]["matches_PR44_snapshot"])
                self.assertTrue(report["unresolved"])

    def test_cli_refuses_output_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            args = (HERE / "examples/dense_4b.json", "--output", path)
            self.assertEqual(self.run_cli(*args).returncode, 0)
            original = path.read_bytes()
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertEqual(path.read_bytes(), original)

    def test_duplicate_key_nan_and_invalid_input_do_not_write_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "input.json", Path(tmp) / "out.json"
            for text in ('{"x":1,"x":2}', '{"x":NaN}', '{}'):
                source.write_text(text, encoding="utf-8")
                run = self.run_cli(source, "--output", output)
                self.assertEqual(run.returncode, 2)
                self.assertFalse(output.exists())
                self.assertNotIn("Traceback", run.stderr)

    def test_unicode_external_input_and_custom_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            config = e.read_json(HERE / "examples/dense_4b.json")
            config["model"]["name"] = "\u6a21\u578b-\U0001f9ee"
            source.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            run = self.run_cli(source, "--candidate", HERE / "profiles/block_candidate_v1.json")
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report["model"]["name"], config["model"]["name"])
            self.assertFalse(report["provenance"]["source_bound"])

    def test_extreme_numeric_units_fail_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            config = e.read_json(HERE / "examples/dense_4b.json")
            config["hardware"].update(clock_hz=1e-300, matrix_utilization=1e-300)
            source.write_text(json.dumps(config), encoding="utf-8")
            run = self.run_cli(source, "--candidate", HERE / "profiles/block_candidate_v1.json")
            self.assertEqual(run.returncode, 2)
            self.assertNotIn("Traceback", run.stderr)


if __name__ == "__main__":
    unittest.main()
