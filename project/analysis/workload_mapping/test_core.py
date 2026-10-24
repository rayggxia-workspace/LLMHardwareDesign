"""Contract tests for finite graph conversion; no model, GPU or EDA execution."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

try:
    from . import core, examples
except ImportError:
    from project.analysis.workload_mapping import core, examples


class MappingTests(unittest.TestCase):
    def reject(self, graph, blocks, message=None):
        if message:
            with self.assertRaisesRegex(core.InputError, message):
                core.build(graph, blocks)
        else:
            with self.assertRaises(core.InputError):
                core.build(graph, blocks)

    def test_all_examples_are_finite_and_deterministic(self):
        for builder in (examples.minimal, examples.reuse, examples.state_feedback,
                        lambda: examples.attention(True), examples.attention,
                        examples.blocks_replacement, examples.alias_copy_transport):
            with self.subTest(builder=builder):
                graph, blocks = builder()
                before = copy.deepcopy((graph, blocks))
                first = core.build(graph, blocks)
                second = core.build(graph, blocks)
                self.assertEqual(core.canonical(first), core.canonical(second))
                self.assertEqual((graph, blocks), before)
                self.assertEqual(first["summary"]["logical"]["status"], "pass")
                self.assertEqual(first["summary"]["physical"]["status"], "not_executed")

    def test_minimal_known_storage_and_payload(self):
        graph, blocks = examples.minimal()
        result = core.build(graph, blocks)
        mapping = result["mapping_request"]
        self.assertEqual(mapping["storage"]["peak_bytes"],
                         {"host": 4, "matrix": 20, "vector": 10})
        self.assertEqual(mapping["storage"]["unique_weight_elements"], 8)
        self.assertEqual(mapping["storage"]["alias_capacity_bytes"], 0)
        self.assertEqual(len(mapping["communication"]), 2)
        first, second = mapping["communication"]
        self.assertEqual((first["payload_bits"], first["container_bytes"]), (32, 4))
        self.assertEqual((second["payload_bits"], second["container_bytes"]), (64, 8))
        self.assertEqual(first["path"], ["host", "matrix"])
        self.assertEqual(second["path"], ["matrix", "vector"])

    def test_repeated_calls_are_not_extra_compute_instances(self):
        graph, blocks = examples.reuse()
        matrix_calls = [c for c in graph["calls"] if c["resource"] == "matrix"]
        self.assertEqual(len(matrix_calls), 2)
        result = core.build(graph, blocks)
        self.assertEqual(sum(r["id"] == "matrix" for r in result["mapping_request"]["resources"]), 1)
        self.assertEqual(result["mapping_request"]["storage"]["unique_weight_elements"], 16)

    def test_three_step_convolution_and_recurrent_feedback(self):
        graph, blocks = examples.state_feedback()
        self.assertEqual(len(graph["states"]), 2)
        self.assertEqual([len(s["versions"]) for s in graph["states"]], [3, 3])
        self.assertEqual(sum(n["semantic"] == "convolution" for n in graph["nodes"]), 3)
        for state in graph["states"]:
            previous = state["initial"]
            for version in state["versions"]:
                self.assertEqual(version["previous"], previous)
                previous = version["tensor"]
        self.assertEqual(core.build(graph, blocks)["summary"]["logical"]["status"], "pass")

    def test_alias_copy_transport_known_values(self):
        graph, blocks = examples.alias_copy_transport()
        result = core.build(graph, blocks)["mapping_request"]
        self.assertEqual(result["storage"]["peak_bytes"], {
            "matrix": 52, "vector_left": 52, "vector_right": 52, "forwarder": 0,
        })
        communication = result["communication"]
        wide = communication[0]
        self.assertEqual(wide["path"], ["matrix", "forwarder", "vector_left"])
        self.assertEqual((wide["payload_bits"], wide["container_bytes"], wide["metadata_bytes"]),
                         (132, 32, 8))
        self.assertEqual(wide["transport"]["payload_bytes"], 40)
        # Fixed #41 reference profile: 64-byte header, 128-byte frame alignment.
        self.assertEqual(wide["transport"]["wire_bytes"], 128)
        self.assertEqual(wide["transport"]["hop_summed_wire_bytes_per_step"], 256)
        self.assertEqual(result["transport"]["shared_TX"]["matrix"]["accounted_wire_bytes_per_step"], 512)
        self.assertEqual(sum(t["transport"]["hop_summed_wire_bytes_per_step"]
                             for t in communication), 768)
        self.assertEqual(result["storage"]["alias_capacity_bytes"], 0)
        self.assertEqual(sum(t["role"] == "scale" for t in graph["tensors"]), 1)

    def test_intermediate_forwarder_requires_route_capability(self):
        graph, blocks = examples.alias_copy_transport()
        forwarder = next(r for r in blocks["resources"] if r["id"] == "forwarder")
        forwarder["capabilities"] = []
        self.reject(graph, blocks, "route|forward|intermediate")

    def test_config_shapes_are_not_a_numeric_trace(self):
        graph, blocks = examples.attention()
        tensors = {t["id"]: t for t in graph["tensors"]}
        self.assertEqual(tensors["t_w_q"]["shape"], [1024, 2048])
        self.assertEqual(tensors["t_w_k"]["shape"], [1024, 1024])
        self.assertEqual(tensors["t_w_o"]["shape"], [2048, 1024])
        self.assertEqual(tensors["t_w_down"]["shape"], [3072, 1024])
        self.assertEqual(tensors["t_decode_k_append"]["shape"], [3, 8, 128])
        self.assertEqual(graph["evidence"]["kind"], "config_derived")
        self.assertEqual(blocks["evidence"]["kind"], "synthetic")
        self.assertEqual({e["phase"] for e in graph["events"]}, {"prefill", "decode"})

    def test_unknown_metadata_preserves_unknown_packet_cost(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["metadata_bytes"] = None
        result = core.build(graph, blocks)
        first = result["mapping_request"]["communication"][0]
        self.assertIsNone(first["metadata_bytes"])
        self.assertIsNone(first["transport"])
        self.assertTrue(any("metadata" in s for s in result["mapping_request"]["assumptions"]))

    def test_i33_uses_i64_container(self):
        graph, blocks = examples.minimal()
        t = next(t for t in graph["tensors"] if t["id"] == "t_matmul")
        t["logical_bits"], t["storage_bits"] = 33, 64
        for storage in graph["storages"]:
            if storage["id"] in ("s_matmul", "s_copy_t_matmul_to_vector"):
                storage["size_bytes"] = 16
        result = core.build(graph, blocks)
        communication = result["mapping_request"]["communication"][1]
        self.assertEqual(communication["payload_bits"], 66)
        self.assertEqual(communication["container_bytes"], 16)
        self.assertEqual(communication["storage_bits"], 64)

    def test_unknown_capacity_does_not_become_zero(self):
        graph, blocks = examples.minimal()
        blocks["resources"][0]["capacity_bytes"] = None
        result = core.build(graph, blocks)
        self.assertTrue(any("capacity unknown" in s for s in result["mapping_request"]["assumptions"]))
        self.assertEqual(result["mapping_request"]["storage"]["peak_bytes"]["host"], 4)

    def test_replacement_inventory_keeps_workload_unchanged(self):
        graph, original = examples.minimal()
        replacement_graph, replacement = examples.blocks_replacement("wider")
        self.assertEqual(graph, replacement_graph)
        self.assertNotEqual(core.digest(original), core.digest(replacement))
        first = core.build(graph, original)
        second = core.build(graph, replacement)
        self.assertEqual(first["mapping_request"]["graph_sha256"], second["mapping_request"]["graph_sha256"])
        self.assertNotEqual(first["mapping_request"]["blocks_sha256"], second["mapping_request"]["blocks_sha256"])

    def test_missing_reference(self):
        graph, blocks = examples.minimal()
        graph["calls"][0]["reads"][0] = "t_missing"
        self.reject(graph, blocks, "missing")

    def test_unknown_field_is_rejected(self):
        graph, blocks = examples.minimal()
        graph["free_bandwidth"] = True
        self.reject(graph, blocks, "unknown")

    def test_duplicate_id(self):
        graph, blocks = examples.minimal()
        graph["nodes"][0]["id"] = graph["calls"][0]["id"]
        graph["calls"][0]["node"] = graph["nodes"][0]["id"]
        self.reject(graph, blocks, "duplicate")

    def test_invalid_shapes(self):
        for shape in ([0, 4], [-1, 4], [True, 4], []):
            with self.subTest(shape=shape):
                graph, blocks = examples.minimal()
                graph["tensors"][0]["shape"] = shape
                self.reject(graph, blocks)

    def test_axes_rank_and_duplicates(self):
        for axes in (["single"], ["same", "same"]):
            graph, blocks = examples.minimal()
            graph["tensors"][0]["axes"] = axes
            self.reject(graph, blocks)

    def test_shape_requires_storage_capacity(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["shape"] = [2, 4]
        self.reject(graph, blocks, "allocation")

    def test_i33_in_i32_rejected(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["logical_bits"] = 33
        graph["tensors"][0]["storage_bits"] = 32
        self.reject(graph, blocks)

    def test_producer_claim_must_match_writes(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["producer"] = graph["calls"][0]["id"]
        self.reject(graph, blocks, "producer")

    def test_incomplete_consumers(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["consumers"] = []
        self.reject(graph, blocks, "consumer")

    def test_early_consumer_rejected(self):
        graph, blocks = examples.minimal()
        index = next(i for i, event in enumerate(graph["events"])
                     if event["ref"] == "tr_t_matmul_to_vector")
        graph["events"][index - 1], graph["events"][index] = graph["events"][index], graph["events"][index - 1]
        for i, event in enumerate(graph["events"]):
            event["step"] = i
        self.reject(graph, blocks, "resident|production")

    def test_missing_transfer_cannot_use_global_tensor(self):
        graph, blocks = examples.minimal()
        removed = graph["transfers"].pop()
        graph["events"] = [e for e in graph["events"] if e["ref"] != removed["id"]]
        for storage in graph["storages"]:
            storage["end"] = graph["events"][-1]["id"]
        self.reject(graph, blocks, "resident")

    def test_storage_lifetime_is_enforced(self):
        graph, blocks = examples.minimal()
        storage = next(s for s in graph["storages"] if s["id"] == "s_copy_t_input_to_matrix")
        storage["end"] = graph["events"][0]["id"]
        self.reject(graph, blocks, "resident|lifetime")

    def test_premature_overwrite_of_live_weight(self):
        graph, blocks = examples.reuse()
        weight = next(t for t in graph["tensors"] if t["id"] == "t_weight")
        result = next(t for t in graph["tensors"] if t["id"] == "t_matrix_first")
        result["storage"] = weight["storage"]
        self.reject(graph, blocks, "premature overwrite")

    def test_in_place_write_requires_new_version(self):
        graph, blocks = examples.minimal()
        graph["calls"][0]["writes"] = [graph["calls"][0]["reads"][0]]
        self.reject(graph, blocks, "new tensor version")

    def test_state_previous_version_is_required(self):
        graph, blocks = examples.state_feedback()
        graph["states"][0]["versions"][1]["previous"] = graph["states"][0]["initial"]
        self.reject(graph, blocks, "previous state")

    def test_state_writer_must_read_previous(self):
        graph, blocks = examples.state_feedback()
        state = graph["states"][0]
        previous = state["initial"]
        writer = next(c for c in graph["calls"] if c["id"] == state["versions"][0]["writer"])
        writer["reads"].remove(previous)
        next(t for t in graph["tensors"] if t["id"] == previous)["consumers"].remove(writer["id"])
        self.reject(graph, blocks, "read previous")

    def test_unowned_state_rejected(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["role"] = "state"
        self.reject(graph, blocks, "lineage")

    def test_dangling_state_version_rejected(self):
        graph, blocks = examples.state_feedback()
        graph["states"][0]["versions"][0]["tensor"] = "missing"
        self.reject(graph, blocks, "missing")

    def test_link_path_direction(self):
        graph, blocks = examples.minimal()
        graph["transfers"][0]["path"] = [blocks["links"][1]["id"]]
        self.reject(graph, blocks, "path")

    def test_link_path_missing(self):
        graph, blocks = examples.minimal()
        graph["transfers"][0]["path"] = []
        self.reject(graph, blocks, "path")

    def test_interface_protocol_mismatch_needs_adapter(self):
        graph, blocks = examples.minimal()
        blocks["links"][0]["protocol"] = "axi"
        self.reject(graph, blocks, "adapter")

    def test_interface_width_mismatch_needs_adapter(self):
        graph, blocks = examples.minimal()
        blocks["resources"][0]["ports"][1]["width_bits"] = 64
        self.reject(graph, blocks, "adapter")

    def test_resource_capability_missing(self):
        graph, blocks = examples.minimal()
        next(r for r in blocks["resources"] if r["id"] == "matrix")["capabilities"] = []
        self.reject(graph, blocks, "capability")

    def test_declared_capacity_is_a_real_gate(self):
        graph, blocks = examples.blocks_replacement("capacity_limited")
        self.reject(graph, blocks, "capacity")

    def test_small_fifo_is_rejected(self):
        graph, blocks = examples.minimal()
        for resource in blocks["resources"]:
            for port in resource["ports"]:
                port["fifo_bytes"] = 1
        self.reject(graph, blocks, "FIFO")

    def test_negative_metadata_rejected(self):
        graph, blocks = examples.minimal()
        graph["tensors"][0]["metadata_bytes"] = -1
        self.reject(graph, blocks)

    def test_messages_are_positive_integer_copies(self):
        for messages in (0, -1, 1.5, True):
            graph, blocks = examples.minimal()
            graph["transfers"][0]["messages"] = messages
            self.reject(graph, blocks)

    def test_alias_is_a_view_not_an_extra_allocation(self):
        graph, blocks = examples.minimal()
        original = graph["tensors"][0]
        alias = copy.deepcopy(original)
        alias.update(id="t_input_view", producer=None, initial=False,
                     alias_of=original["id"])
        graph["tensors"].append(alias)
        original["consumers"] = []
        graph["calls"][0]["reads"][0] = alias["id"]
        result = core.build(graph, blocks)
        self.assertEqual(result["mapping_request"]["storage"]["peak_bytes"]["host"], 4)
        self.assertEqual(result["mapping_request"]["storage"]["alias_capacity_bytes"], 0)

    def test_alias_cannot_hide_an_allocated_copy(self):
        graph, blocks = examples.minimal()
        original = graph["tensors"][0]
        alias = copy.deepcopy(original)
        alias.update(id="t_bad_view", producer=None, initial=False,
                     alias_of=original["id"], storage="s_weight", consumers=[])
        graph["tensors"].append(alias)
        self.reject(graph, blocks, "alias")

    def test_partial_alias_copy_cannot_supply_whole_tensor(self):
        graph, blocks = examples.minimal()
        original = graph["tensors"][0]
        view = copy.deepcopy(original)
        view.update(id="t_partial_view", shape=[1, 2], producer=None,
                    initial=False, alias_of=original["id"], consumers=[])
        graph["tensors"].append(view)
        graph["transfers"][0]["tensor"] = view["id"]
        self.reject(graph, blocks, "not resident|coverage|range")

    def test_shared_output_requires_explicit_route_capability(self):
        graph, blocks = examples.attention(True)
        for resource in blocks["resources"]:
            resource["capabilities"] = [
                c for c in resource["capabilities"] if c["semantic"] != "route"
            ]
        self.reject(graph, blocks, "route|mux|output|fanout")

    def test_shared_input_requires_explicit_route_capability(self):
        graph, blocks = examples.attention(True)
        source = next(r for r in blocks["resources"] if r["id"] == "matrix")
        source["capabilities"] = [
            c for c in source["capabilities"] if c["semantic"] != "route"
        ]
        self.reject(graph, blocks, "route|mux|input|fanin|arbiter")

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="mapping-test-", dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version": "a", "schema_version": "b"}', encoding="utf-8")
            with self.assertRaisesRegex(core.InputError, "duplicate JSON key"):
                core.read_json(path)

    def test_nonfinite_json_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="mapping-test-", dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "nonfinite.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(core.InputError, "nonfinite"):
                core.read_json(path)


if __name__ == "__main__":
    unittest.main()
