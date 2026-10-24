"""Known-value and protocol negative tests. Fixtures/expected are read-only."""
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import replay as r

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def fixture(graph, kind="input"):
    return r.read_json(FIX / f"{graph}.{kind}.json")


class Graph1Tests(unittest.TestCase):
    def setUp(self):
        self.config = fixture("graph1_reduce_rq")

    def test_hand_values_and_independent_expected(self):
        result = r.replay(self.config)
        r.compare(result, fixture("graph1_reduce_rq", "expected"))
        # Dot products expanded independently of the group loop.
        self.assertEqual(2 - 2, result["partials"][0][0])
        self.assertEqual(-4 - 1, result["partials"][0][1])
        self.assertEqual(-3 + 0, result["partials"][1][0])
        self.assertEqual(3 + 8, result["partials"][1][1])
        self.assertEqual(result["complete"], [-3, 6])
        self.assertEqual(result["rq_codes"], [-2, 3])
        self.assertEqual(result["consumer_codes"], [-1, 1])

    def test_negative_and_positive_rne_ties_independent_fraction_oracle(self):
        self.assertEqual([r.rne_div(n, 2) for n in [-7, -5, -3, -1, 1, 3, 5, 7]],
                         [-4, -2, -2, 0, 0, 2, 2, 4])
        for divisor in [2, 3, 4, 7, 128]:
            for value in range(-513, 514):
                self.assertEqual(r.rne_div(value, divisor), round(Fraction(value, divisor)))

    def test_early_rq_is_an_illegal_different_function(self):
        result = r.replay(self.config)
        self.assertEqual(result["illegal_early_rq_codes"], [-2, 4])
        self.assertFalse(result["early_rq_equivalent"])
        self.config["protocol"]["rq_position"] = "per_partial"
        with self.assertRaisesRegex(r.ContractError, "protocol"):
            r.replay(self.config)

    def test_missing_group(self):
        self.config["data"]["groups"].pop()
        with self.assertRaisesRegex(r.ContractError, "missing K group"):
            r.replay(self.config)

    def test_duplicate_group(self):
        self.config["data"]["groups"][1] = copy.deepcopy(self.config["data"]["groups"][0])
        with self.assertRaisesRegex(r.ContractError, "duplicate K group"):
            r.replay(self.config)

    def test_partial_unit_dtype_shape_range_or_route_mismatch(self):
        for key, value in [("unit", 2), ("dtype", "INT64"), ("shape", [1]),
                           ("k_start", 1), ("path", ["M", "S", "V"])]:
            config = copy.deepcopy(self.config)
            config["data"]["groups"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(r.ContractError, "group"):
                r.replay(config)

    def test_tensor_dtype_shape_storage_layout_and_signedness(self):
        for key, value in [("dtype", "INT16"), ("shape", [2, 2]), ("storage_bits", 16),
                           ("layout", "K,output_channel"), ("signedness", "unsigned"), ("unit", 2),
                           ("logical_bits", 7), ("values", [2, -1, 3]), ("values", [2, -1, 3, 128])]:
            config = copy.deepcopy(self.config)
            config["data"]["x"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(r.ContractError):
                r.replay(config)

    def test_insufficient_private_fifo_or_instances(self):
        for field, key, value in [("private_bytes", "M", 51), ("private_bytes", "V", 63), ("instances", "M", 0)]:
            config = copy.deepcopy(self.config)
            config["resources"][field][key] = value
            with self.subTest(field=field, key=key), self.assertRaises(r.ContractError):
                r.replay(config)
        self.config["resources"]["endpoint_fifo_bytes"] = 127
        with self.assertRaisesRegex(r.ContractError, "FIFO"):
            r.replay(self.config)

    def test_saturation_is_explicit_only_at_rq(self):
        self.assertEqual([r.sat8(x) for x in [-129, -128, 127, 128]], [-128, -128, 127, 127])
        self.config["data"]["x"]["values"] = [127] * 4
        self.config["data"]["W"]["values"] = [[127] * 4, [-128] * 4]
        result = r.replay(self.config)
        self.assertEqual(result["complete"], [64516, -65024])
        self.assertEqual(result["rq_codes"], [127, -128])
        self.assertEqual(result["consumer_codes"], [128, -130])

    def test_communication_and_memory_independent_arithmetic(self):
        result = r.replay(self.config)
        t = result["runtime_traffic"]
        self.assertEqual(t["logical_payload_bytes"], 2 * 2 * 4)
        self.assertEqual(t["physical_bytes"], 2 * (64 + 64))
        self.assertEqual(t["link_beats"], 256 // 16)
        self.assertEqual(result["storage"]["peak_reserved_bytes"], {"M": 52, "V": 64})
        self.assertEqual(result["storage"]["total_reserved_bytes"], 52 + 64 + 2 * 128)

    def test_reordered_input_groups_preserves_declared_reduce_order(self):
        self.config["data"]["groups"].reverse()
        self.assertEqual(r.replay(self.config)["partials"], [[0, -5], [-3, 11]])


class Graph2Tests(unittest.TestCase):
    def setUp(self):
        self.config = fixture("graph2_state_commit")
        self.steps = self.config["data"]["steps"]

    def test_hand_states_and_independent_expected(self):
        result = r.replay(self.config)
        r.compare(result, fixture("graph2_state_commit", "expected"))
        self.assertEqual([c["state"] for c in result["normal"]["commits"]], [[3, 0], [2, 4], [5, 2]])
        self.assertEqual([c["version"] for c in result["normal"]["commits"]], [1, 2, 3])

    def test_failure_is_private_retry_commits_once(self):
        m = r.StateMachine(self.config)
        m.step(self.steps[0])
        published = (list(m.state), list(m.snapshot), copy.deepcopy(m.commits), m.version)
        with self.assertRaisesRegex(r.TrialAborted, "private trial discarded"):
            m.step(self.steps[1], fail_before_commit=True)
        self.assertEqual((m.state, m.snapshot, m.commits, m.version), published)
        self.assertEqual(m.state, [3, 0])
        self.assertEqual(m.version, 1)
        self.assertEqual(m.payloads, [4, 4, 4])  # no failed-trial state packet
        m.step(self.steps[1])
        self.assertEqual(m.state, [2, 4])
        self.assertEqual(m.version, 2)
        with self.assertRaisesRegex(r.ContractError, "step|version"):
            m.step(self.steps[1])
        self.assertEqual(len(m.commits), 2)

    def test_wrong_owner_version_epoch_and_unit_are_rejected(self):
        for key, value in [("owner", "S"), ("expected_version", 0), ("epoch", 1), ("unit", 2)]:
            m = r.StateMachine(self.config)
            m.step(self.steps[0])
            bad = copy.deepcopy(self.steps[1])
            bad[key] = value
            before = m.summary()
            with self.subTest(key=key), self.assertRaisesRegex(r.ContractError, key):
                m.step(bad)
            self.assertEqual(m.summary(), before)

    def test_int16_overflow_rejects_whole_vector_without_saturation(self):
        # Lane 0 is valid, lane 1 overflows: neither lane is committed.
        self.config["data"]["s0"]["values"] = [0, 32767]
        m = r.StateMachine(self.config)
        with self.assertRaisesRegex(r.ContractError, "guard.*INT16"):
            m.step(self.steps[0])
        self.assertEqual(m.state, [0, 32767])
        self.assertEqual(m.snapshot, [0, 32767])
        self.assertEqual(m.version, 0)
        self.assertEqual(m.commits, [])
        self.assertEqual(m.payloads, [4])
        self.assertEqual([b["op"] for b in m.bank], ["read_input"])

    def test_negative_overflow_is_also_rejected(self):
        self.config["data"]["s0"]["values"] = [-32768, 0]
        self.config["data"]["steps"][0]["values"] = [-1, 0]
        m = r.StateMachine(self.config)
        with self.assertRaisesRegex(r.ContractError, "guard"):
            m.step(self.config["data"]["steps"][0])
        self.assertEqual(m.state, [-32768, 0])

    def test_real_file_save_restore_and_chunk_continuity(self):
        full = r.StateMachine(self.config)
        for step in self.steps:
            full.step(step)
        prefix = r.StateMachine(self.config)
        prefix.step(self.steps[0])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            path.write_text(r.canonical(prefix.checkpoint()), encoding="utf-8")
            resumed = r.StateMachine.restore(self.config, r.read_json(path))
        self.assertEqual(resumed.state, [3, 0])
        self.assertEqual(resumed.version, 1)
        for step in self.steps[1:]:
            resumed.step(step)
        self.assertEqual(resumed.summary(), full.summary())
        self.assertEqual(resumed.state, [5, 2])

    def test_chunk_reset_old_request_and_corrupt_checkpoint_rejected(self):
        m = r.StateMachine(self.config)
        m.step(self.steps[0])
        for key, value in [("state", [1, -1]), ("version", 0), ("epoch", 1), ("unit", 2), ("owner", "S")]:
            saved = m.checkpoint()
            saved["body"][key] = value
            # Rehash so semantic validation, rather than digest alone, must reject.
            saved["sha256"] = hashlib.sha256(r.canonical(saved["body"]).encode()).hexdigest()
            with self.subTest(key=key), self.assertRaises(r.ContractError):
                r.StateMachine.restore(self.config, saved)
        saved = m.checkpoint()
        saved["body"]["state"][0] = 999
        with self.assertRaisesRegex(r.ContractError, "digest"):
            r.StateMachine.restore(self.config, saved)
        fresh = r.StateMachine(self.config)
        with self.assertRaisesRegex(r.ContractError, "step|version"):
            fresh.step(self.steps[1])

    def test_state_snapshot_and_input_are_copies_not_aliases(self):
        m = r.StateMachine(self.config)
        result = m.step(self.steps[0])
        result["state"][0] = 999
        m.snapshot[0] = -999
        self.assertEqual(m.state, [3, 0])
        self.assertEqual(m.commits[0]["state"], [3, 0])
        self.assertEqual(self.config["data"]["s0"]["values"], [1, -1])

    def test_s_1rw_actions_serialized_including_failed_read(self):
        result = r.replay(self.config)
        for scenario, expected_ops in [("normal", ["read_input", "write_snapshot"] * 3),
                                       ("failure_retry", ["read_input", "write_snapshot", "read_input", "read_input", "write_snapshot", "read_input", "write_snapshot"])]:
            bank = result[scenario]["s_bank_schedule"]
            self.assertEqual([b["slot"] for b in bank], list(range(len(bank))))
            self.assertEqual([b["op"] for b in bank], expected_ops)
        self.config["protocol"]["s_port"] = "1R1W"
        with self.assertRaises(r.ContractError):
            r.replay(self.config)

    def test_capacity_includes_proposal_input_shadow_and_metadata(self):
        result = r.replay(self.config)
        self.assertEqual(result["storage"]["peak_reserved_bytes"], {"R": 52, "S": 44})
        self.assertEqual(result["storage"]["total_reserved_bytes"], 52 + 44 + 4 * 128)
        for block, capacity in [("R", 8), ("R", 51), ("S", 43)]:
            config = copy.deepcopy(self.config)
            config["resources"]["private_bytes"][block] = capacity
            with self.subTest(block=block, capacity=capacity), self.assertRaisesRegex(r.ContractError, "capacity"):
                r.replay(config)

    def test_normal_and_retry_traffic_exact_totals(self):
        result = r.replay(self.config)
        self.assertEqual(result["normal"]["runtime_traffic"]["physical_bytes"], 6 * 128)
        self.assertEqual(result["normal"]["runtime_traffic"]["link_beats"], 768 // 16)
        self.assertEqual(result["failure_retry"]["runtime_traffic"]["physical_bytes"], 7 * 128)
        self.assertEqual(result["failure_retry"]["runtime_traffic"]["link_beats"], 896 // 16)


class ContractAndCLITests(unittest.TestCase):
    def cli(self, source, expected, *extra):
        return subprocess.run([sys.executable, "-B", str(HERE / "replay.py"), str(source),
                               "--expected", str(expected), *map(str, extra)],
                              capture_output=True, encoding="utf-8")

    def test_both_graphs_two_cli_runs_identical_and_read_only(self):
        paths = list(FIX.glob("*.json"))
        before = {p: p.read_bytes() for p in paths}
        for name in ["graph1_reduce_rq", "graph2_state_commit"]:
            source, expected = FIX / f"{name}.input.json", FIX / f"{name}.expected.json"
            first, second = self.cli(source, expected), self.cli(source, expected)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            r.compare(json.loads(first.stdout), r.read_json(expected))
        self.assertEqual({p: p.read_bytes() for p in paths}, before)

    def test_wrong_expected_returns_nonzero_without_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            expected, output = Path(tmp) / "wrong.json", Path(tmp) / "out.json"
            wrong = fixture("graph1_reduce_rq", "expected")
            wrong["rq_codes"] = [-2, 4]
            expected.write_text(json.dumps(wrong), encoding="utf-8")
            run = self.cli(FIX / "graph1_reduce_rq.input.json", expected, "--output", output)
            self.assertEqual(run.returncode, 2)
            self.assertIn("expected mismatch at $.rq_codes[1]", run.stderr)
            self.assertFalse(output.exists())

    def test_tampered_input_rejected_even_with_recomputed_expected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, expected = Path(tmp) / "input.json", Path(tmp) / "expected.json"
            changed = fixture("graph1_reduce_rq")
            changed["data"]["x"]["values"][0] = 1
            source.write_text(json.dumps(changed), encoding="utf-8")
            # A test-only attacker creates a separate temp expected, never fixture expected.
            expected.write_text(json.dumps(r.replay(changed)), encoding="utf-8")
            run = self.cli(source, expected)
            self.assertEqual(run.returncode, 2)
            self.assertIn("fixture SHA-256 mismatch: input", run.stderr)

    def test_cli_missing_group_wrong_owner_and_capacity_errors(self):
        changes = [("graph1_reduce_rq", lambda c: c["data"]["groups"].pop()),
                   ("graph2_state_commit", lambda c: c["data"]["steps"][1].update(owner="S")),
                   ("graph2_state_commit", lambda c: c["resources"]["private_bytes"].update(R=8))]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            for name, change in changes:
                config = fixture(name)
                change(config)
                source.write_text(json.dumps(config), encoding="utf-8")
                run = self.cli(source, FIX / f"{name}.expected.json")
                self.assertEqual(run.returncode, 2)
                self.assertIn("ERROR:", run.stderr)
                self.assertNotIn("Traceback", run.stderr)

    def test_cli_refuses_overwrite_and_input_expected_paths(self):
        source = FIX / "graph1_reduce_rq.input.json"
        expected = FIX / "graph1_reduce_rq.expected.json"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            first = self.cli(source, expected, "--output", output)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            second = self.cli(source, expected, "--output", output)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), original)
        for protected in (source, expected):
            before = protected.read_bytes()
            run = self.cli(source, expected, "--output", protected)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(protected.read_bytes(), before)

    def test_duplicate_keys_nan_unknown_and_bool_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            for text in ['{"x":1,"x":2}', '{"x":NaN}', '{}', '[]']:
                source.write_text(text, encoding="utf-8")
                run = self.cli(source, FIX / "graph1_reduce_rq.expected.json")
                self.assertEqual(run.returncode, 2)
                self.assertNotIn("Traceback", run.stderr)
        for field, value in [("extra", 1), ("source_commit", "main"), ("graph_id", "other")]:
            config = fixture("graph1_reduce_rq")
            config[field] = value
            with self.assertRaises(r.ContractError):
                r.replay(config)
        config = fixture("graph1_reduce_rq")
        config["data"]["x"]["values"][0] = True
        with self.assertRaises(r.ContractError):
            r.replay(config)

    def test_nodes_dependencies_link_and_metadata_are_contractual(self):
        for graph in ["graph1_reduce_rq", "graph2_state_commit"]:
            for field, value in [("header_bytes", 32), ("hops", 2), ("metadata_in_header", False),
                                 ("bits", 64), ("max_packet_bytes", 4096)]:
                config = fixture(graph)
                config["link"][field] = value
                with self.subTest(graph=graph, field=field), self.assertRaises(r.ContractError):
                    r.replay(config)
            config = fixture(graph)
            config["nodes"][-1]["depends_on"] = []
            with self.assertRaisesRegex(r.ContractError, "dependencies"):
                r.replay(config)

    def test_packet_boundaries_fragmentation_and_no_zero_unknown(self):
        for payload, packets, wire, beats in [(4, 1, 128, 8), (8, 1, 128, 8),
                                               (1984, 1, 2048, 128), (1985, 2, 2176, 136)]:
            p = r.packet(payload)
            self.assertEqual((p["packets"], p["physical_bytes"], p["link_beats"]), (packets, wire, beats))
        for bad in [0, None, True, -1]:
            with self.assertRaises(r.ContractError):
                r.packet(bad)

    def test_replay_purity_and_determinism(self):
        for graph in ["graph1_reduce_rq", "graph2_state_commit"]:
            config = fixture(graph)
            before = copy.deepcopy(config)
            first, second = r.replay(config), r.replay(config)
            self.assertEqual(first, second)
            self.assertEqual(config, before)

    def test_checked_in_fixture_digests(self):
        digests = r.read_json(FIX / "sha256.json")
        self.assertEqual(len(digests), 4)
        for name, digest in digests.items():
            self.assertEqual(hashlib.sha256((FIX / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
