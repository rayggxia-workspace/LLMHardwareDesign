import copy
import json
import unittest
from pathlib import Path
import layout
import verify


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((Path(__file__).parent/"contract.json").read_text(encoding="utf-8"))
        cls.profiles = {p["id"]: p for p in cls.cfg["profiles"]}
        cls.p = cls.profiles["h2560_stream_gamma"]
        cls.trace = list(layout.events(cls.p, cls.cfg))

    def reject(self, change, profile=None):
        trace = copy.deepcopy(self.trace)
        change(trace)
        with self.assertRaises(ValueError):
            verify.verify_trace(trace, profile or self.p, self.cfg)

    def test_all_profiles_and_independent_counts(self):
        for p in self.profiles.values():
            self.assertEqual(layout.check_layout(p), verify.layout_result(p))
            self.assertEqual(verify.layout_result(p)["valid"], p["expect_valid"])
            if "mode" in p:
                trace = list(layout.events(p, self.cfg))
                self.assertEqual(verify.verify_trace(trace, p, self.cfg), layout.counters(trace, self.cfg))

    def test_full_h2560_fit_and_explicit_gap(self):
        result = verify.layout_result(self.p)
        self.assertEqual(result["active_bytes_by_phase"], {"norm": 15872})
        self.assertEqual(16384-result["active_bytes_by_phase"]["norm"], 512)

    def test_gamma_stream_saves_exact_reread_traffic(self):
        resident = verify.verify_trace(self.trace, self.p, self.cfg)
        p = self.profiles["h2560_stream_xy_gamma"]
        streamed = verify.verify_trace(list(layout.events(p, self.cfg)), p, self.cfg)
        self.assertEqual(resident["external_transactions"], 1920)
        self.assertEqual(resident["store_operations"], 4480)
        self.assertEqual(streamed["external_transactions"]-resident["external_transactions"], 640)
        self.assertEqual(streamed["prototype_wire_bytes"]-resident["prototype_wire_bytes"], 51200)
        self.assertEqual(streamed["store_operations"]-resident["store_operations"], 640)

    def test_existing1536_complete_io_counts(self):
        p = self.profiles["h1536_resident_existing"]
        c = verify.verify_trace(list(layout.events(p, self.cfg)), p, self.cfg)
        self.assertEqual((c["external_transactions"], c["store_operations"], c["prototype_wire_bytes"]), (1152, 2688, 92160))

    def test_frame_cache_alias_rejected(self):
        p = copy.deepcopy(self.p)
        next(r for r in p["regions"] if r["name"] == "V")["start"] = 12288
        self.assertFalse(verify.layout_result(p)["valid"])

    def test_full_gamma_cannot_be_added(self):
        self.assertFalse(verify.layout_result(self.profiles["h2560_naive_full_gamma"])["valid"])

    def test_disjoint_lifetimes_may_overlay(self):
        p = copy.deepcopy(self.profiles["h1536_post_m_overlay"])
        self.assertTrue(verify.layout_result(p)["valid"])
        next(r for r in p["regions"] if r["name"] == "V")["live"].append("m")
        self.assertFalse(verify.layout_result(p)["valid"])

    def test_invalid_alignment(self):
        p = copy.deepcopy(self.p)
        p["regions"][0]["start"] = 1
        self.assertFalse(verify.layout_result(p)["valid"])

    def test_boolean_address_rejected(self):
        self.reject(lambda t: t[0].__setitem__(2, True))

    def test_global_statistics_cannot_omit_line(self):
        self.reject(lambda t: t.pop(next(i for i,e in enumerate(t) if len(e)==6 and e[-1]=="stats")))

    def test_duplicate_statistics_rejected(self):
        def change(t):
            i = next(i for i,e in enumerate(t) if len(e)==6 and e[-1]=="stats")
            t.insert(i, t[i][:])
        self.reject(change)

    def test_per_tile_denominator_rejected(self):
        def change(t):
            i = next(i for i,e in enumerate(t) if e[:2]==["C","NORM"])
            t.insert(i, ["C","DEN",256])
        self.reject(change)

    def test_wrong_gamma_line_rejected(self):
        def change(t):
            e = next(e for e in t if len(e)==6 and e[:2]==["S","R"] and e[3]=="G")
            e[4] += 1
        self.reject(change)

    def test_gamma_requires_drain_before_next_tile(self):
        self.reject(lambda t: t.pop(next(i for i,e in enumerate(t) if e[:2]==["C","GAMMA_RELEASE"])))

    def test_gamma_release_requires_all_lines(self):
        def change(t):
            e = next(e for e in t if e[:2]==["C","GAMMA_RELEASE"])
            e[3] -= 1
        self.reject(change)

    def test_store_write_requires_external_source(self):
        self.reject(lambda t: t.pop(0))

    def test_output_requires_complete_consumer(self):
        self.reject(lambda t: t.pop(next(i for i,e in enumerate(t) if e[:2]==["C","NORM"])))

    def test_external_capacity_is_single_response(self):
        self.reject(lambda t: t.insert(1, t[0][:]))

    def test_cache_or_guard_write_rejected(self):
        def change(t):
            e = next(e for e in t if len(e)==6 and e[:2]==["S","W"])
            e[2] = 12288
        self.reject(change)

    def test_egress_before_read_rejected(self):
        self.reject(lambda t: t.pop(next(i for i,e in enumerate(t) if len(e)==6 and e[:2]==["S","R"] and e[3]=="Y")))

    def test_after_completion_rejected(self):
        self.reject(lambda t: t.append(["C","DONE",2560]))

    def test_missing_completion_rejected(self):
        self.reject(lambda t: t.pop())

    def test_cannot_shrink_xy_to_free_frame(self):
        p = copy.deepcopy(self.p)
        p["regions"][0]["bytes"] -= 512
        self.reject(lambda t: None, p)


if __name__ == "__main__":
    unittest.main()
