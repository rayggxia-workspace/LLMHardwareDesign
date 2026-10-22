from copy import deepcopy
import itertools
import json
from pathlib import Path
import unittest

from graph import Infeasible, make_graph, verify_access_order
from scheduler import schedule, validate_schedule


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(Path(__file__).with_name("experiment.json").read_text())["base"]
        self.cfg.update(max_query_tile=2, key_tile=4)
        self.workload = dict(queries=2, keys=5, head_dim=4)
        self.placement = dict(O=0, m=1, l=0)

    def make(self, **kwargs):
        return make_graph(self.cfg, self.workload, self.placement, **kwargs)

    def test_tail_shapes_all_placements_ports_and_policies(self):
        for ports, bits in itertools.product(("1RW", "1R1W", "2RW"), itertools.product((0, 1), repeat=3)):
            self.cfg["bank_ports"] = ports
            self.placement = dict(zip(("O", "m", "l"), bits))
            graph = self.make()
            # Full source/load/output bytes, including one-element final key tile.
            self.assertEqual(graph["traffic"]["D"], 2*(2*4+5*4)*4)
            self.assertEqual(graph["matrix_macs"], 2*2*5*4)
            for policy in ("critical", "fifo", "shortest", "longest"):
                result = schedule(graph["tasks"], graph["capacities"], policy)
                self.assertTrue(validate_schedule(graph["tasks"], graph["capacities"], result)["valid"])
                self.assertEqual(verify_access_order(graph, result), [])

    def test_static_capacity_and_scratch_are_not_pooled(self):
        graph = self.make()
        self.cfg["bank_bytes"] = [graph["bank_reserved_bytes"][0]-1, 10**9]
        with self.assertRaises(Infeasible):
            self.make()
        self.cfg["bank_bytes"] = [10**9, 10**9]
        self.cfg["scratch_bytes"]["V"] = graph["scratch_reserved_bytes"]["V"]-1
        with self.assertRaises(Infeasible):
            self.make()

    def test_static_max_allocation_same_across_phases(self):
        first = self.make()
        self.workload["queries"] = 1
        last = self.make()
        self.assertEqual(first["slots"], last["slots"])
        self.assertEqual(first["scratch_reserved_bytes"], last["scratch_reserved_bytes"])

    def test_no_free_bandwidth_or_invalid_precision_dimensions(self):
        for key in ("bank_port_bytes_per_cycle", "matrix_macs_per_cycle", "external_bytes_per_cycle"):
            for invalid in (0, -1, True, float("nan"), 1.1):
                cfg = dict(self.cfg, **{key: invalid})
                with self.assertRaises(ValueError):
                    make_graph(cfg, self.workload, self.placement)
        with self.assertRaises(ValueError):
            self.make(disabled=["unknown"])

    def test_label_zero_effect_and_disabled_edge(self):
        first = self.make()
        second = self.make(boundary="joined")
        first.pop("boundary_label")
        second.pop("boundary_label")
        self.assertEqual(first, second)
        with self.assertRaises(Infeasible):
            self.make(disabled=["M0"])
        self.placement = dict(O=1, m=1, l=1)
        self.assertEqual(self.make()["tasks"], self.make(disabled=["V0"])["tasks"])

    def test_address_extent_direction_and_version_mutations(self):
        graph = self.make()
        result = schedule(graph["tasks"], graph["capacities"])
        for tid, field, value in (("t1.qk.rK", "bytes", 64), ("t1.loadK", "bytes", 4),
                                   ("entry.Q", "direction", "X"), ("entry.Q", "offset", 64),
                                   ("entry.Q", "bank", 2)):
            broken = deepcopy(graph)
            next(a for a in broken["accesses"] if a["id"] == tid)[field] = value
            self.assertTrue(verify_access_order(broken, result), (tid, field))
        broken = deepcopy(graph)
        broken["slots"]["Q"]["bank"] = 2
        for a in broken["accesses"]:
            if a["object"] == "Q":
                a["bank"] = 2
        self.assertTrue(verify_access_order(broken, result))

    def test_removed_dependency_is_not_repaired_by_address_lock(self):
        graph = self.make()
        # Address locks prevent simultaneous access, but cannot choose the
        # correct version: force the future K load before its old reader.
        broken = deepcopy(graph)
        load = next(t for t in broken["tasks"] if t["id"] == "t1.loadK")
        load["deps"] = []
        load["duration"] = 1
        result = schedule(broken["tasks"], broken["capacities"], "shortest")
        self.assertTrue(validate_schedule(broken["tasks"], broken["capacities"], result)["valid"])
        self.assertTrue(verify_access_order(broken, result))


if __name__ == "__main__":
    unittest.main()
