"""Independent exhaustive checks of the six paired ablation controls.

Run with Python -B to avoid creating bytecode in a shared review worktree.
The test materializer deliberately does not import the campaign's materializer.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

FROZEN_ROUTING = Path(__file__).resolve().parents[1] / "frozen_routing"
sys.path.insert(0, str(FROZEN_ROUTING))

from model import digest
from oracle import feasible, solve
from validate import validate
from tiny_cases import ARMS, cases


def materialize_for_test(master, overlay):
    """Pure copy/restriction using the explicit fixture contract only."""
    allowed = overlay["allowed_connectors"]
    capacities = overlay["tap_capacities"]
    if len(set(allowed)) != len(allowed) or not set(allowed) <= set(master["connectors"]):
        raise ValueError("overlay connector set is not an inventory subset")
    if set(capacities) != set(master["taps"]):
        raise ValueError("fixture overlays must explicitly describe every tap")
    result = copy.deepcopy(master)
    result["connectors"] = {key: result["connectors"][key] for key in allowed}
    for tap, capacity in capacities.items():
        maximum = master["taps"][tap]["capacity"]
        if type(capacity) is not int or not 0 < capacity <= maximum:
            raise ValueError("overlay capacity exceeds inventory")
        component = master["components"][master["taps"][tap]["component"]]
        if component["kind"] != "wire" and capacity != 1:
            raise ValueError("input/output pin capacity must remain one")
        result["taps"][tap]["capacity"] = capacity
    return result


def subsets(keys):
    keys = sorted(keys)
    for mask in range(1 << len(keys)):
        yield [key for i, key in enumerate(keys) if mask & (1 << i)]


def selected_validation(base, nets, keys):
    return validate(base, nets,
                    {"base_sha256": digest(base), "connectors": list(keys)},
                    digest(base))


class TinyCasesTests(unittest.TestCase):
    def test_inventory_contract_and_fresh_return_values(self):
        fixtures = cases()
        self.assertEqual([c["name"] for c in fixtures], [
            "access-only", "capacity-only", "joint-required",
            "driver-short", "positive", "budget-fail"])
        fresh_hash = digest(cases())
        for case in fixtures:
            with self.subTest(case=case["name"]):
                master = case["master"]
                self.assertLessEqual(len(master["connectors"]), 16)
                self.assertEqual(set(case["overlays"]), set(ARMS))
                before = digest(master)
                for overlay in case["overlays"].values():
                    base = materialize_for_test(master, overlay)
                    self.assertEqual(base["components"], master["components"])
                    self.assertEqual(base["blocks"], master["blocks"])
                    self.assertEqual(base["limits"], master["limits"])
                    for tap, info in base["taps"].items():
                        self.assertEqual(info["component"], master["taps"][tap]["component"])
                        self.assertEqual(info["site"], master["taps"][tap]["site"])
                    for key, info in base["connectors"].items():
                        self.assertEqual(info, master["connectors"][key])
                self.assertEqual(digest(master), before)
        fixtures[0]["master"]["components"].clear()
        self.assertEqual(digest(cases()), fresh_hash)

    def test_exact_arm_expectations_and_optima(self):
        optimum = {"access-only": 3, "capacity-only": 4,
                   "joint-required": 4, "positive": 2}
        for case in cases():
            for arm in ARMS:
                with self.subTest(case=case["name"], arm=arm):
                    base = materialize_for_test(case["master"], case["overlays"][arm])
                    answer = solve(base, case["nets"])
                    expected = case["expected_feasible"][arm]
                    self.assertEqual(answer is not None, expected)
                    if answer is not None:
                        self.assertEqual(answer[0], optimum[case["name"]])
                        self.assertTrue(selected_validation(base, case["nets"], answer[1])["valid"])

    def test_every_subset_validator_matches_independent_oracle(self):
        # These are all possible manufactured connector choices, including
        # useless branches and shorts, not just solutions returned by a router.
        for case in cases():
            for arm in ARMS:
                base = materialize_for_test(case["master"], case["overlays"][arm])
                for selected in subsets(base["connectors"]):
                    with self.subTest(case=case["name"], arm=arm, selected=selected):
                        actual = selected_validation(base, case["nets"], selected)["valid"]
                        self.assertEqual(actual, feasible(base, case["nets"], selected))

    def test_every_feasible_witness_survives_constraint_relaxation(self):
        pairs = [("restricted", "access"), ("restricted", "capacity"),
                 ("restricted", "joint"), ("access", "joint"),
                 ("capacity", "joint")]
        for case in cases():
            bases = {arm: materialize_for_test(case["master"], case["overlays"][arm])
                     for arm in ARMS}
            for source, target in pairs:
                for selected in subsets(bases[source]["connectors"]):
                    if feasible(bases[source], case["nets"], selected):
                        with self.subTest(case=case["name"], source=source,
                                          target=target, selected=selected):
                            self.assertTrue(feasible(bases[target], case["nets"], selected))
                            self.assertTrue(selected_validation(
                                bases[target], case["nets"], selected)["valid"])

    def test_capacity_and_joint_controls_fail_for_the_intended_constraint(self):
        fixtures = {case["name"]: case for case in cases()}
        for name, arm in (("capacity-only", "restricted"),
                          ("capacity-only", "access"),
                          ("joint-required", "access")):
            case = fixtures[name]
            base = materialize_for_test(case["master"], case["overlays"][arm])
            required = ["drive", "sink0", "sink1", "sink2"]
            self.assertEqual(selected_validation(base, case["nets"], required)["errors"],
                             ["endpoint_capacity"])

    def test_missing_access_is_not_cured_by_capacity(self):
        for case in cases():
            if case["name"] not in ("access-only", "joint-required"):
                continue
            for arm in ("restricted", "capacity"):
                base = materialize_for_test(case["master"], case["overlays"][arm])
                result = selected_validation(base, case["nets"], sorted(base["connectors"]))
                self.assertIn("disconnected_sink", result["errors"])
                self.assertNotIn("endpoint_capacity", result["errors"])

    def test_driver_short_persists_without_capacity_or_budget_failures(self):
        case = next(c for c in cases() if c["name"] == "driver-short")
        required = ["drive0", "drive1", "sink0", "sink1"]
        for arm in ARMS:
            base = materialize_for_test(case["master"], case["overlays"][arm])
            result = selected_validation(base, case["nets"], required)
            self.assertIn("multiple_drivers", result["errors"])
            self.assertNotIn("endpoint_capacity", result["errors"])
            self.assertNotIn("connector_budget", result["errors"])
            self.assertNotIn("disconnected_sink", result["errors"])

    def test_fixed_global_budget_is_the_only_chain_failure(self):
        case = next(c for c in cases() if c["name"] == "budget-fail")
        for arm in ARMS:
            base = materialize_for_test(case["master"], case["overlays"][arm])
            selected = sorted(base["connectors"])
            self.assertEqual(selected_validation(base, case["nets"], selected)["errors"],
                             ["connector_budget"])
            # This countercheck is local to the test, never an experiment arm.
            hypothetical = copy.deepcopy(base)
            hypothetical["limits"]["custom_connector_budget"] = 4
            self.assertTrue(feasible(hypothetical, case["nets"], selected))


if __name__ == "__main__":
    unittest.main()
