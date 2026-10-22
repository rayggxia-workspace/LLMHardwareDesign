import copy
import unittest
from study import (ARMS, WORKLOADS, assert_contract, classify_group, demands, digest,
                   lifted_witness, make_inventory, materialize, no_path_certificates,
                   route, seeded_mapping, validate)
from tiny_cases import cases
from verify_ablation import verify_cut


class OverlayTests(unittest.TestCase):
    def test_original_resources_and_nested_overlays(self):
        for tracks in (1, 2):
            for span in (1, 2):
                for access in (2, 4):
                    master, overlays = make_inventory(tracks, span, access)
                    before = digest(master)
                    bases = assert_contract(master, overlays)
                    self.assertEqual(digest(master), before)
                    self.assertEqual(bases["capacity"]["taps"], bases["joint"]["taps"])
                    self.assertNotEqual(digest(bases["restricted"]), digest(bases["joint"]))

    def test_overlay_rejects_new_contact_and_unknown_fields(self):
        master, overlays = make_inventory(1, 1, 2)
        for kind in ("unknown", "duplicate", "new_field"):
            overlay = copy.deepcopy(overlays["restricted"])
            if kind == "unknown":
                overlay["allowed_connectors"].append("invented interior tap")
            elif kind == "duplicate":
                overlay["allowed_connectors"].append(overlay["allowed_connectors"][0])
            else:
                overlay["active_buffer"] = True
            with self.assertRaises(ValueError):
                materialize(master, overlay)

    def test_capacity_arm_cannot_silently_expand_access(self):
        master, overlays = make_inventory(1, 1, 2)
        extra = next(k for k in overlays["access"]["allowed_connectors"]
                     if k not in overlays["restricted"]["allowed_connectors"])
        overlays["capacity"]["allowed_connectors"].append(extra)
        with self.assertRaises(AssertionError):
            assert_contract(master, overlays)

    def test_overlay_rejects_bad_or_raised_capacities(self):
        master, overlays = make_inventory(1, 1, 2)
        tap = next(iter(master["taps"]))
        for value in (True, float("nan"), 0, -1, 1.0, master["taps"][tap]["capacity"] + 1):
            overlay = copy.deepcopy(overlays["restricted"])
            overlay["tap_capacities"][tap] = value
            with self.assertRaises(ValueError):
                materialize(master, overlay)
        overlay = copy.deepcopy(overlays["restricted"])
        del overlay["tap_capacities"][tap]
        with self.assertRaises(ValueError):
            materialize(master, overlay)

    def test_pin_capacity_cannot_be_relaxed(self):
        master, overlays = make_inventory(1, 1, 2)
        overlay = copy.deepcopy(overlays["joint"])
        overlay["tap_capacities"]["S0.o:0"] = 2
        with self.assertRaises(ValueError):
            materialize(master, overlay)

    def test_independent_cut_check_detects_false_certificate(self):
        case = next(c for c in cases() if c["name"] == "access-only")
        base = materialize(case["master"], case["overlays"]["restricted"])
        certs = no_path_certificates(base, case["nets"])
        self.assertTrue(certs)
        for cert in certs:
            verify_cut(base, case["nets"], cert)
        expanded = materialize(case["master"], case["overlays"]["access"])
        with self.assertRaises(AssertionError):
            verify_cut(expanded, case["nets"], certs[0])

    def test_witness_is_rebound_and_revalidated_without_changing_connections(self):
        case = next(c for c in cases() if c["name"] == "access-only")
        restricted = materialize(case["master"], case["overlays"]["restricted"])
        expanded = materialize(case["master"], case["overlays"]["access"])
        solution = {"base_sha256": digest(expanded), "connectors": sorted(expanded["connectors"])}
        self.assertTrue(validate(expanded, case["nets"], solution)["valid"])
        self.assertIsNone(lifted_witness(restricted, case["nets"], solution))
        copied = lifted_witness(expanded, case["nets"], solution)
        self.assertEqual(copied, solution)
        self.assertIsNot(copied["connectors"], solution["connectors"])

    def test_known_feasible_miss_is_never_counted_as_router_success(self):
        master, overlays = make_inventory(2, 1, 4)
        bases = assert_contract(master, overlays)
        workload = WORKLOADS["ffn"]
        mapping = seeded_mapping(workload, 17)
        solution = route(bases["restricted"], demands(workload, mapping), "multi_order", 17, 12)
        self.assertIsNotNone(solution)
        rows = [{"arm": arm, "workload": "ffn", "seed": 17, "mapping": mapping,
                 "raw_solution": solution if arm == "restricted" else None} for arm in ARMS]
        classified = classify_group(rows, bases)
        self.assertEqual(classified[0]["knowledge"], "routed")
        for row in classified[1:]:
            self.assertIsNone(row["raw_solution"])
            self.assertEqual(row["knowledge"], "known_feasible_heuristic_miss")
            witness = row["imported_witness"]
            self.assertEqual(witness["source_arm"], "restricted")
            self.assertEqual(witness["solution"]["connectors"], solution["connectors"])
            self.assertEqual(witness["solution"]["base_sha256"], digest(bases[row["arm"]]))


if __name__ == "__main__":
    unittest.main()
