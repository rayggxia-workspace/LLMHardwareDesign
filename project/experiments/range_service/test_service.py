"""Small synthetic service-boundary tests, no model/tensor execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

sp = importlib.util.spec_from_file_location("issue68_service_test", Path(__file__).with_name("service.py"))
S = importlib.util.module_from_spec(sp)
sp.loader.exec_module(S)


def task(attempts=None):
    return {"norm_rows": 1, "tokens": [{"attempts": attempts or [{"accepted": True, "epoch": 0}]}],
            "precision": {"state_bits": 32}, "commit_contract": "synthetic same atomic contract"}


class ServiceTest(unittest.TestCase):
    def test_config_and_capacity_reject(self):
        with self.assertRaises(ValueError):
            S.config(tile=64)
        g = S.Graph(S.config())
        with self.assertRaisesRegex(ValueError, "capacity"):
            g.slot("bad", "R", 32000, 2000)
        with self.assertRaisesRegex(ValueError, "overlap"):
            g.slot("bad", "V", 0, 10)

    def test_R_old_new_aux_fit(self):
        a, b = S.Graph(S.config(tile=16)), S.Graph(S.config(tile=32))
        self.assertEqual(a.new_bank, "R")
        self.assertEqual(b.new_bank, "S4")
        self.assertEqual(sum(x["bytes"] for x in a.allocations if x["bank"] == "R"), 24576)
        self.assertEqual(sum(x["bytes"] for x in b.allocations if x["bank"] == "R"), 24576)
        self.assertTrue(any(x["id"] == "R.new_shadow" and x["bytes"] == 16384 for x in b.allocations))

    def test_fragment_port_credit_and_padding(self):
        g = S.Graph(S.config(ext_ii=16))
        g.packet("EXT", "R", 2000)
        self.assertEqual(len(g.nodes), 2)
        self.assertEqual([x["meta"]["payload_bytes"] for x in g.nodes], [1984, 16])
        n = g.nodes[1]
        self.assertEqual(n["duration"], 16 + 3 + 1)
        self.assertEqual(n["meta"]["wire_bytes"], 48)
        w = S.schedule(g)
        self.assertEqual(S.audit(w)["resource_high_water"]["FIFO:R:RX"], 1984)

    def test_label_only_controls_identical(self):
        for suffix in ("2_6", "4_4", "6_2"):
            a = S.schedule(S.graph(task(), S.config("shared" + suffix)))
            b = S.schedule(S.graph(task(), S.config("split" + suffix)))
            self.assertEqual(a["makespan"], b["makespan"])
            self.assertEqual([(x["start"], x["end"], x["reservations"]) for x in a["nodes"]],
                             [(x["start"], x["end"], x["reservations"]) for x in b["nodes"]])

    def test_dependency_and_port_tampering_reject(self):
        g = S.Graph(S.config())
        a = g.control("a", [], cycles=3)
        g.control("b", [a], cycles=2)
        w = S.schedule(g)
        z = copy.deepcopy(w)
        z["nodes"][1].update(start=0, end=2)
        with self.assertRaisesRegex(ValueError, "dependency"):
            S.audit(z)
        z["nodes"][1]["deps"] = []
        with self.assertRaisesRegex(ValueError, "resource capacity"):
            S.audit(z)

    def test_full_group_guard_before_output_and_commit(self):
        g = S.graph(task(), S.config(tile=32))
        guards = [x["id"] for x in g.nodes if x["kind"] == "attempt_guard_barrier"]
        outputs = [x["id"] for x in g.nodes if x["meta"].get("operation") == "new_state_completeK_output"]
        commit = next(x for x in g.nodes if x["kind"] == "atomic_group_commit")
        self.assertTrue(outputs and min(outputs) > max(guards))
        self.assertGreater(commit["id"], max(outputs))
        self.assertEqual(commit["meta"]["descriptor_bytes"], 70)
        self.assertTrue(any(x["resource"] == "PORT:R" for x in commit["reservations"]))

    def test_failed_attempt_no_output_and_complete_trial_clone(self):
        t = task([{"accepted": False, "epoch": 0, "rescale_heads": [1]},
                  {"accepted": True, "epoch": 1}])
        g = S.graph(t, S.config(tile=16))
        self.assertFalse(any(x["meta"].get("attempt") == 0 and
                             x["meta"].get("operation") == "new_state_completeK_output" for x in g.nodes))
        clones = [x for x in g.nodes if x["meta"].get("operation") == "clone_full_committed_trial"]
        self.assertEqual(sum(x["meta"]["payload_bytes"] for x in clones if x["meta"]["src"] == "EXT"), 131072)
        self.assertEqual({x["meta"]["head"] for x in clones}, {0, 1})
        self.assertEqual(S.audit(S.schedule(g))["status"], "PASS")

    def test_norm_routes_are_alternatives_and_wide_work_not_free(self):
        for route in ("reread", "spill"):
            g = S.Graph(S.config(norm_route=route))
            S.build_norm(g, 0, [])
            packets = [x["meta"] for x in g.nodes if x["kind"] == "packet"]
            operations = {x["operation"] for x in packets}
            self.assertEqual("aligned_spill" in operations, route == "spill")
            self.assertEqual("reread_mixed" in operations, route == "reread")
            self.assertEqual(sum(x["payload_bytes"] for x in packets if x["operation"] == "gamma_stream"), 10240)
            self.assertEqual(sum(x["payload_bytes"] for x in packets if x["operation"] == "publish_fresh_A8"), 2612)
        self.assertEqual(S.mulslots(10, 3), 320)


if __name__ == "__main__":
    unittest.main()
