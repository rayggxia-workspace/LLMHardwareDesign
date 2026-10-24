"""Contract, finite-credit, full-head and mixed-protocol negative checks."""
import copy
import unittest

from service import GROUPS, ORGANIZATIONS, audit, build, config, inventory, lut_bytes


class AttentionServiceTests(unittest.TestCase):
    def small(self, organization="split", group="gemma_local0", kv_bits=8, queries=1):
        g = build(config(group=group, organization=organization, kv_bits=kv_bits,
                         queries=queries, keys=128, exp_ii=1))
        scheduled = g.schedule("critical")
        return g, scheduled

    def test_closed_interval_rom_capacity_and_same_assets(self):
        self.assertEqual(lut_bytes(128), 8196)
        self.assertEqual(lut_bytes(256), 16388)
        with self.assertRaisesRegex(ValueError, "LUT_ROM_capacity"):
            config(rom_bytes=8192)
        with self.assertRaisesRegex(ValueError, "LUT_ROM_capacity"):
            config(lut_step=256, rom_bytes=16384)
        assets = [inventory(config(organization=o)) for o in ORGANIZATIONS]
        self.assertEqual(assets[0], assets[1])
        self.assertEqual(assets[0], assets[2])

    def test_colocation_label_is_exact_zero_change(self):
        a = build(config(organization="split"))
        b = build(config(organization="colocated_control"))
        self.assertEqual(a.nodes, b.nodes)
        self.assertEqual(a.packets, b.packets)
        self.assertEqual(a.bytes, b.bytes)
        for policy in ("fifo", "critical"):
            ar, br = a.schedule(policy), b.schedule(policy)
            self.assertEqual(ar, br)
            self.assertEqual(audit(a, ar), audit(b, br))

    def test_internal_stream_only_saves_headers_and_retains_bus(self):
        a, ar = self.small()
        b, br = self.small("colocated_stream")
        self.assertTrue(b.streams)
        self.assertEqual(a.expected, b.expected)
        self.assertEqual(a.operations, b.operations)
        self.assertEqual(a.bytes["wire_payload"], b.bytes["wire_payload"])
        self.assertEqual(a.bytes["memory_logical"], b.bytes["memory_logical"])
        self.assertEqual(a.bytes["memory_physical"], b.bytes["memory_physical"])
        self.assertEqual(a.bytes["wire"] - b.bytes["wire"], len(b.streams) * 64)
        self.assertTrue(all("bus" in b.nodes[p["wire"]]["resources"] for p in b.streams))
        audit(a, ar)
        audit(b, br)

    def test_full_GQA_shapes_causal_rows_and_PV_products(self):
        for group, spec in GROUPS.items():
            g = build(config(group=group, queries=4, kv_bits=16))
            e = g.expected
            self.assertEqual(e["heads"], spec["heads"])
            self.assertEqual(e["valid_elements"], spec["heads"] * (125 + 126 + 127 + 128))
            self.assertEqual(e["PV_S8_products"], 9)
            self.assertEqual(e["K_backing_bytes"], spec["heads"] * 128 * spec["dim"] * 2)
            self.assertEqual(e["V_backing_bytes"], e["K_backing_bytes"])
            r = g.schedule("fifo")
            audit(g, r)

    def test_one_lookup_port_and_division_sensitivity(self):
        a = build(config(exp_ii=1))
        b = build(config(exp_ii=32))
        for g in (a, b):
            exp_nodes = [n for n in g.nodes if n["label"] == "exp LUT one read port"]
            div_nodes = [n for n in g.nodes if n["label"] == "U64 restoring normalize divide"]
            self.assertEqual(sum(n["elements"] for n in exp_nodes), 2 * g.expected["valid_elements"])
            self.assertEqual(sum(n["elements"] for n in div_nodes), g.expected["valid_elements"])
            self.assertTrue(all(n["duration"] == n["elements"] * g.config["exp_ii"] for n in exp_nodes))
            self.assertTrue(all(n["duration"] == n["elements"] * 64 for n in div_nodes))
        self.assertGreater(b.schedule("critical")["cycles"], a.schedule("critical")["cycles"])

    def test_long_context_capacity_and_matrix_limb_offsets(self):
        g = build(config(group="qwen25_global0", keys=1024, queries=4,
                         kv_bits=16, organization="colocated_stream", exp_ii=8))
        audit(g, g.schedule("critical"))
        self.assertEqual(g.expected["heads"], 8)
        self.assertEqual(g.expected["PV_matrix_calls"], 8 * 8 * 8 * 9)
        self.assertEqual(g.expected["K_backing_bytes"], 8 * 1024 * 128 * 2)
        first = next(n for n in g.nodes if n["label"] == "PV S8 limb")
        first["a_offset"] = 4096
        with self.assertRaisesRegex(AssertionError, "matrix operand capacity"):
            audit(g, g.schedule("critical"))

    def test_reject_packet_truncation_and_removed_bus(self):
        g, scheduled = self.small("colocated_stream")
        packet = g.streams[0]
        original = packet["payload"]
        packet["payload"] -= 1
        with self.assertRaises(AssertionError):
            audit(g, scheduled)
        packet["payload"] = original
        node = g.nodes[packet["wire"]]
        node["resources"].remove("bus")
        with self.assertRaises(AssertionError):
            audit(g, scheduled)

    def test_reject_dependency_capacity_and_missing_GQA_head(self):
        g, scheduled = self.small()
        packet = g.packets[0]
        wire = g.nodes[packet["wire"]]
        wire["deps"].remove(packet["read"])
        with self.assertRaises(AssertionError):
            audit(g, scheduled)
        g, scheduled = self.small()
        memory = next(n for n in g.nodes if "port" in n)
        memory["offset"] = g.sizes[memory["port"]]
        with self.assertRaises(AssertionError):
            audit(g, scheduled)
        g, scheduled = self.small()
        g.expected["PV_matrix_calls"] += 1
        with self.assertRaisesRegex(AssertionError, "missing GQA"):
            audit(g, scheduled)

    def test_reject_endpoint_credit_overlap(self):
        g, scheduled = self.small("colocated_stream")
        # Corrupt the read interval of an internal stream into the preceding
        # source packet's TX lease. The independent interval checker must reject.
        bad = copy.deepcopy(scheduled)
        p = g.streams[0]
        bad["trace"][p["read"]][0] = 0
        with self.assertRaises(AssertionError):
            audit(g, bad)


if __name__ == "__main__":
    unittest.main()
