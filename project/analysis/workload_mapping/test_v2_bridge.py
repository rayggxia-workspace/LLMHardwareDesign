"""Fixed v2 acceptance, original arithmetic calls and generic typed conversion."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from project.analysis.workload_mapping import v2_bridge as bridge
from project.analysis.workload_mapping.core import build
from project.analysis.workload_mapping.consumer import verify_mapping
from project.analysis.workload_mapping.semantics import apply_semantics, validate_semantics


class V2BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_root = Path(os.environ.get("TMPDIR", bridge.REPO / "runs" / "tmp")).resolve()
        if not cls.tmp_root.is_relative_to(bridge.REPO):
            raise RuntimeError("test temporary root outside task checkout")
        cls.tmp_root.mkdir(parents=True, exist_ok=True)

    def fixed(self, name="graph1_reduce_rq", scenario="normal"):
        return bridge.accept_fixed(bridge.UPSTREAM / "fixtures" / (name + ".input.json"),
                                   bridge.UPSTREAM / "fixtures" / (name + ".expected.json"), scenario)

    def built(self, name="graph1_reduce_rq", scenario="normal"):
        graph, blocks, semantics, actual = self.fixed(name, scenario)
        result = build(graph, blocks)
        apply_semantics(result, graph, blocks, semantics)
        return graph, blocks, semantics, actual, result

    def test_graph1_original_arithmetic_and_independent_oracle_accept(self):
        graph, blocks, semantics, actual, result = self.built()
        self.assertEqual(actual["partials"], [[0, -5], [-3, 11]])
        self.assertEqual(actual["complete"], [-3, 6])
        self.assertEqual(actual["rq_codes"], [-2, 3])
        self.assertEqual(actual["consumer_codes"], [-1, 1])
        self.assertFalse(actual["early_rq_equivalent"])
        self.assertEqual(result["mapping_request"]["storage"]["peak_bytes"], {"M": 52, "V": 64})
        self.assertEqual(len([c for c in graph["calls"] if c["resource"] == "M"]), 2)
        self.assertEqual(len([r for r in blocks["resources"] if r["id"] == "M"]), 1)
        self.assertEqual(semantics["reductions"][0]["expected_groups"], [0, 1])

    def test_all_scenarios_traffic_matches_replayed_independent_expected(self):
        for name, scenario in (("graph1_reduce_rq", "normal"), ("graph2_state_commit", "normal"),
                               ("graph2_state_commit", "failure_retry")):
            with self.subTest(name=name, scenario=scenario):
                graph, blocks, semantics, actual, result = self.built(name, scenario)
                oracle = actual if name == "graph1_reduce_rq" else actual[scenario]
                communications = result["mapping_request"]["communication"]
                self.assertEqual(len(communications), oracle["runtime_traffic"]["messages"])
                self.assertEqual(sum(t["container_bytes"] for t in communications),
                                 oracle["runtime_traffic"]["logical_payload_bytes"])
                self.assertEqual(sum(t["transport"]["wire_bytes"] for t in communications),
                                 oracle["runtime_traffic"]["physical_bytes"])
                self.assertEqual(sum(t["transport"]["ideal_link_cycles"] for t in communications),
                                 oracle["runtime_traffic"]["link_beats"])
                verify_mapping(result["mapping_request"])

    def test_graph2_normal_has_three_commits_and_separate_snapshot_copies(self):
        graph, blocks, semantics, actual, result = self.built("graph2_state_commit")
        self.assertEqual(actual["normal"]["final_state"], [5, 2])
        self.assertEqual([tx["version"] for tx in semantics["transactions"]], [1, 2, 3])
        self.assertTrue(all(tx["outcome"] == "commit" for tx in semantics["transactions"]))
        self.assertEqual(len(graph["states"][0]["versions"]), 3)
        formats = semantics["tensor_formats"]
        self.assertEqual(len([f for f in formats if f["stage"] == "SNAPSHOT"]), 4)
        self.assertEqual(result["mapping_request"]["storage"]["peak_bytes"], {"R": 52, "S": 44})
        self.assertIsNone(result["resource_input"])

    def test_graph1_resource_export_replays_with_original_estimator_cli(self):
        graph, blocks, semantics, actual, result = self.built()
        exported = result["resource_input"]
        self.assertEqual(exported["model"]["total_parameters"], 8)
        self.assertEqual(exported["model"]["linear_ops"][0]["instances"], 1)
        self.assertEqual(exported["placement"]["weights"], "unknown")
        self.assertEqual(len(exported["transfers"]), 2)
        self.assertFalse(result["summary"]["resource_projection"]["full_graph_compatible"])
        estimator = bridge.HERE.parent / "llm_resources"
        with tempfile.TemporaryDirectory(prefix="v2-", dir=self.tmp_root) as tmp:
            input_path, output_path = Path(tmp) / "resource_input.json", Path(tmp) / "report.json"
            input_path.write_text(json.dumps(exported), encoding="utf-8")
            done = subprocess.run([sys.executable, "-B", str(estimator / "estimate.py"), str(input_path),
                                   "--candidate", str(estimator / "profiles/block_candidate_v1.json"),
                                   "--output", str(output_path)], capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            provenance = report.pop("provenance")
            self.assertTrue(provenance["matches_PR44_snapshot"])
            self.assertEqual(report, result["resource_report"])
            self.assertEqual(report["reference_transport"]["shared_TX"]["M"]
                             ["accounted_wire_bytes_per_step"], 256)
            self.assertIsNone(report["reference_transport"]["shared_TX"]["M"]
                              ["required_bytes_per_second"])

    def test_failure_retry_never_publishes_failed_generation_and_resends_input(self):
        graph, blocks, semantics, actual, result = self.built("graph2_state_commit", "failure_retry")
        trials = semantics["transactions"]
        self.assertEqual([t["outcome"] for t in trials], ["commit", "abort", "commit", "commit"])
        self.assertEqual([t["version"] for t in trials], [1, 1, 2, 3])
        self.assertIsNone(trials[1]["published"])
        self.assertEqual(trials[1]["previous"], trials[2]["previous"])
        self.assertTrue(trials[1]["guard_pass"])
        calls = {c["id"]: c for c in graph["calls"]}
        self.assertEqual(calls[trials[1]["terminal_call"]]["writes"], [])
        self.assertEqual(len(graph["states"][0]["versions"]), 3)
        step2_inputs = [t for t in graph["transfers"] if t["tensor"] == "t_u2"]
        self.assertEqual(len(step2_inputs), 2)
        self.assertEqual(actual["after_t2_abort"], {"state": [3, 0], "version": 1,
                                                  "snapshot": [3, 0], "published_count": 1})
        self.assertEqual(actual["failure_retry"]["runtime_traffic"]["messages"], 7)

    def test_static_unused_regions_and_fifo_domains_remain_separate(self):
        graph, blocks, semantics, actual, result = self.built("graph2_state_commit", "failure_retry")
        domains = {(d["resource"], d["kind"]): d["bytes"]
                   for d in result["mapping_request"]["semantic_report"]["domain_peak_bytes"]}
        self.assertEqual(domains, {("R", "private_ram"): 52, ("S", "shared_bank"): 44,
                                  ("R", "fifo"): 256, ("S", "fifo"): 256})
        self.assertEqual(sum(domains.values()), actual["storage"]["total_reserved_bytes"])
        self.assertTrue(all(d["kind"] != "fifo" for d in semantics["storage_domains"]))
        stores = {s["id"]: s for s in graph["storages"]}
        self.assertEqual(stores["s_R_control_metadata"]["size_bytes"], 32)
        self.assertEqual(stores["s_S_control_metadata"]["size_bytes"], 24)
        self.assertEqual(stores["s_R_proposal"]["size_bytes"], 8)
        self.assertEqual(stores["s_R_shadow"]["size_bytes"], 4)
        self.assertTrue(all(s["begin"] == graph["events"][0]["id"] and
                            s["end"] == graph["events"][-1]["id"] for s in stores.values()))

    def test_bank_access_sidecar_binds_actual_s1rw_trace_to_graph_events(self):
        for scenario, count in (("normal", 6), ("failure_retry", 7)):
            with self.subTest(scenario=scenario):
                graph, blocks, semantics, actual = self.fixed("graph2_state_commit", scenario)
                self.assertEqual(semantics["bank_ports"], [{"resource": "S", "protocol": "1RW",
                                                          "width_bits": 128}])
                accesses = semantics["bank_accesses"]
                self.assertEqual(len(accesses), count)
                events = {e["id"]: e for e in graph["events"]}
                transfers = {t["id"]: t for t in graph["transfers"]}
                calls = {c["id"]: c for c in graph["calls"]}
                tensors = {t["id"]: t for t in graph["tensors"]}
                stores = {s["id"]: s for s in graph["storages"]}
                bound_trace = []
                for access in accesses:
                    event = events[access["event"]]
                    step = int(event["ref"].split("step", 1)[1].split("_", 1)[0])
                    self.assertEqual(stores[access["storage"]]["resource"], access["resource"])
                    if access["op"] == "read":
                        self.assertEqual(event["kind"], "transfer")
                        self.assertEqual(transfers[event["ref"]]["source_storage"], access["storage"])
                    else:
                        self.assertEqual(event["kind"], "call")
                        self.assertIn(access["storage"], [tensors[t]["storage"]
                                      for t in calls[event["ref"]]["writes"]])
                    bound_trace.append({"slot": access["slot"], "step": step,
                        "op": "read_input" if access["op"] == "read" else "write_snapshot"})
                self.assertEqual(bound_trace, actual[scenario]["s_bank_schedule"])
                self.assertEqual([a["slot"] for a in accesses], list(range(count)))

    def test_convert_calls_original_state_machine_for_abort_and_retry(self):
        upstream = bridge._load_upstream()
        config = upstream.read_json(bridge.UPSTREAM / "fixtures/graph2_state_commit.input.json")
        calls = []
        original = upstream.StateMachine

        class Observed(original):
            def step(self, request, fail_before_commit=False):
                calls.append((request["step"], fail_before_commit))
                return super().step(request, fail_before_commit=fail_before_commit)

        upstream.StateMachine = Observed
        with mock.patch.object(bridge, "_load_upstream", return_value=upstream):
            bridge.convert(config, "failure_retry")
        self.assertEqual(calls, [(1, False), (2, True), (2, False), (3, False)])

    def test_convert_does_not_read_independent_expected_numbers(self):
        upstream = bridge._load_upstream()
        config = upstream.read_json(bridge.UPSTREAM / "fixtures/graph1_reduce_rq.input.json")
        original = Path.read_bytes
        accessed = []

        def checked(path, *args, **kwargs):
            accessed.append(str(path))
            if ".expected.json" in str(path):
                raise AssertionError("convert consulted an expected file")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", checked):
            graph, blocks, semantics = bridge.convert(config)
        self.assertTrue(accessed)
        self.assertEqual(len(graph["transfers"]), 2)

    def test_accept_replays_and_compares_original_implementation(self):
        upstream = bridge._load_upstream()
        with mock.patch.object(bridge, "_load_upstream", return_value=upstream), \
                mock.patch.object(upstream, "replay", wraps=upstream.replay) as replay, \
                mock.patch.object(upstream, "compare", wraps=upstream.compare) as compare:
            self.fixed()
        self.assertEqual(replay.call_count, 1)
        self.assertGreater(compare.call_count, 1)  # Recursive original comparator.

    def test_fixed_accept_rejects_changed_input_or_expected_before_replay(self):
        upstream = bridge._load_upstream()
        with tempfile.TemporaryDirectory(prefix="v2-", dir=self.tmp_root) as tmp:
            changed = Path(tmp) / "changed.json"
            changed.write_text('{}\n', encoding="utf-8")
            with mock.patch.object(bridge, "_load_upstream", return_value=upstream), \
                    mock.patch.object(upstream, "replay", wraps=upstream.replay) as replay:
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    bridge.accept_fixed(bridge.UPSTREAM / "fixtures/graph1_reduce_rq.input.json", changed)
                self.assertEqual(replay.call_count, 0)
            data = upstream.read_json(bridge.UPSTREAM / "fixtures/graph1_reduce_rq.input.json")
            data["data"]["x"]["values"][0] = 3
            changed.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                bridge.accept_fixed(changed, bridge.UPSTREAM / "fixtures/graph1_reduce_rq.expected.json")

    def test_nonfixed_contract_errors_not_coerced_or_silenced(self):
        upstream = bridge._load_upstream()
        config = upstream.read_json(bridge.UPSTREAM / "fixtures/graph1_reduce_rq.input.json")
        missing = copy.deepcopy(config)
        missing["data"]["groups"].pop()
        with self.assertRaisesRegex(ValueError, "group"):
            bridge.convert(missing)
        with self.assertRaisesRegex(ValueError, "only normal"):
            bridge.convert(config, "failure_retry")

    def test_protocol_mutations_are_rejected_after_generic_conversion(self):
        graph, blocks, semantics, actual = self.fixed()
        bad = copy.deepcopy(semantics)
        next(f for f in bad["tensor_formats"] if f["stage"] == "PARTIAL")["unit"] = 2
        with self.assertRaisesRegex(ValueError, "units"):
            validate_semantics(bad, graph, blocks)
        graph, blocks, semantics, actual = self.fixed("graph2_state_commit", "failure_retry")
        bad = copy.deepcopy(semantics)
        bad["transactions"][1]["version"] = 2
        with self.assertRaisesRegex(ValueError, "aborted"):
            validate_semantics(bad, graph, blocks)

    def test_no_private_proposal_or_shadow_is_exported(self):
        graph, blocks, semantics, actual = self.fixed("graph2_state_commit", "failure_retry")
        private = {f["tensor"] for f in semantics["tensor_formats"] if f["stage"] in ("PROPOSAL", "SHADOW")}
        self.assertFalse(private & {t["tensor"] for t in graph["transfers"]})
        calls = {c["id"]: c for c in graph["calls"]}
        for transaction in semantics["transactions"]:
            if transaction["outcome"] == "commit":
                self.assertIn(transaction["previous"], calls[transaction["terminal_call"]]["reads"])
                self.assertIn(transaction["shadow"], calls[transaction["terminal_call"]]["reads"])

    def test_deterministic_conversion_and_cli_output_is_exclusive(self):
        first = self.fixed("graph2_state_commit", "failure_retry")
        self.assertEqual(first, self.fixed("graph2_state_commit", "failure_retry"))
        with tempfile.TemporaryDirectory(prefix="v2-", dir=self.tmp_root) as tmp:
            output = Path(tmp) / "new-output"
            args = [str(bridge.UPSTREAM / "fixtures/graph2_state_commit.input.json"), "--expected",
                    str(bridge.UPSTREAM / "fixtures/graph2_state_commit.expected.json"),
                    "--scenario", "failure_retry", "--output-dir", str(output)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bridge.main(args), 0)
                self.assertEqual(bridge.main(args), 2)
            mapping = json.loads((output / "mapping_request.json").read_text())
            verify_mapping(mapping)
            self.assertEqual(mapping["schema_version"], "mapping-request/2")
            self.assertEqual(len(list(output.glob("*.json"))), 6)


if __name__ == "__main__":
    unittest.main()
