import copy
import itertools
import unittest
from fixtures import tiny, solution
from model import WORKLOADS, demands, digest, make_fabric, seeded_mapping
from numeric import check
from oracle import feasible, solve
from router import route
from validate import validate, validate_mapping


class ElectricalTests(unittest.TestCase):
    def setUp(self):
        self.base, self.nets = tiny()

    def errors(self, keys, nets=None):
        return validate(self.base, self.nets if nets is None else nets,
                        solution(self.base, keys))["errors"]

    def test_legal_independent_networks(self):
        self.assertEqual(self.errors(["j0", "j1", "j2", "j3"]), [])

    def test_indivisible_conductor_short(self):
        # Different endpoints of fixed A are electrically identical. The
        # connectors themselves do not overlap; edge ownership alone misses it.
        self.base["connectors"]["hidden"] = {
            "a": "d1:0", "b": "A:1", "kind": "exposed_join", "cost_units": 1}
        self.assertIn("multiple_drivers", self.errors(["j0", "hidden"]))

    def test_unused_driver_is_still_a_driver(self):
        self.assertIn("multiple_drivers", self.errors(
            ["j0", "j1", "j4", "j9"], [self.nets[0]]))

    def test_illegal_interior_connection(self):
        self.assertIn("illegal_connector", self.errors(["A:middle~C:middle"]))

    def test_endpoint_capacity(self):
        self.assertIn("endpoint_capacity", self.errors(["j2", "j5"]))

    def test_disconnected_and_wrong_driver(self):
        self.assertIn("disconnected_sink", self.errors(["j0"]))
        self.assertIn("wrong_driver", self.errors(["j1", "j9", "j5"]))

    def test_inventory_mutation_cannot_be_hidden_by_rehash(self):
        expected = digest(self.base)
        changed = copy.deepcopy(self.base)
        changed["components"]["A"]["width"] = 32
        result = validate(changed, [], solution(changed, []), expected)
        self.assertIn("fixed_inventory_changed", result["errors"])

    def test_added_active_resource_not_allowed(self):
        s = solution(self.base, [])
        s["new_buffer"] = "magic"
        self.assertIn("undeclared_configuration_field", validate(self.base, [], s)["errors"])

    def test_width_and_sink_conflicts(self):
        nets = copy.deepcopy(self.nets)
        nets[0]["width"] = 32
        self.assertIn("width_mismatch", self.errors(["j0", "j1", "j2", "j3"], nets))
        nets = copy.deepcopy(self.nets)
        nets[1]["sinks"] = ["t0"]
        self.assertIn("different_nets_same_sink", self.errors(["j0", "j2"], nets))

    def test_invalid_width_and_configuration_types(self):
        for width in [float("nan"), 0, -1, True, "16", 16.0]:
            nets = copy.deepcopy(self.nets)
            nets[0]["width"] = width
            self.assertIn("invalid_demand_type_or_width", self.errors([], nets))
            self.assertFalse(feasible(self.base, nets, []))
        for config in [None, [], {"connectors": "j0"}, {"connectors": [None]}]:
            self.assertFalse(validate(self.base, self.nets, config)["valid"])

    def test_mapping_must_match_frozen_capabilities(self):
        base, w = make_fabric(), WORKLOADS["ffn"]
        mapping = {"x": "S0", "y": "S1", "m0": "C0", "m1": "C1", "v0": "C2"}
        self.assertIn("unsupported_operation", validate_mapping(base, w, mapping)["errors"])
        with self.assertRaises(ValueError):
            check("ffn", w, mapping, base, solution(base, []), 17)
        mapping["v0"] = "V0"
        self.assertTrue(validate_mapping(base, w, mapping)["valid"])
        mapping["m1"] = "C0"
        self.assertIn("mapping_not_injective", validate_mapping(base, w, mapping)["errors"])
        mapping["x"] = "S1"
        self.assertIn("io_mapping", validate_mapping(base, w, mapping)["errors"])

    def test_extra_connector_is_not_ignored(self):
        self.assertIn("multiple_drivers", self.errors(["j0", "j1", "j2", "j3", "j4", "j9"]))

    def test_duplicate_and_budget(self):
        self.assertIn("duplicate_connector", self.errors(["j0", "j0"]))
        self.base["limits"]["custom_connector_budget"] = 0
        self.assertIn("connector_budget", self.errors(["j0"]))

    def test_validator_against_exhaustive_independent_oracle(self):
        keys = sorted(self.base["connectors"])
        for mask in range(1 << len(keys)):
            selected = [k for i, k in enumerate(keys) if mask & (1 << i)]
            self.assertEqual(validate(self.base, self.nets, solution(self.base, selected))["valid"],
                             feasible(self.base, self.nets, selected), (mask, selected))

    def test_router_and_tiny_exact_optimum(self):
        for seed in range(12):
            base, nets = tiny(seed)
            exact = solve(base, nets)
            result = route(base, nets, "multi_order", seed, 4)
            if result:
                self.assertIsNotNone(exact)
                self.assertGreaterEqual(validate(base, nets, result)["custom_cost_units"], exact[0])

    def test_span_conserves_prefabricated_wire_budget(self):
        for tracks in (1, 2):
            bases = [make_fabric(tracks, s, 4) for s in (1, 2)]
            lengths = [sum(c["length_units"] for c in b["components"].values()) for b in bases]
            self.assertEqual(lengths[0], lengths[1])
            self.assertNotEqual(len(bases[0]["taps"]), len(bases[1]["taps"]))

    def test_functional_path_reaches_expected_software_result(self):
        base = make_fabric(3, 1, 8)
        for name, workload in WORKLOADS.items():
            result = None
            for seed in range(8):
                mapping = seeded_mapping(workload, seed)
                result = route(base, demands(workload, mapping), "multi_order", seed, 12)
                if result:
                    self.assertTrue(check(name, workload, mapping, base, result, seed)["passed"])
                    break
            self.assertIsNotNone(result, name)


if __name__ == "__main__":
    unittest.main()
