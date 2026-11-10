"""Meaningful guards against source drift, fake density and free SRAM copies."""
import json
import unittest

from baseline import BASELINE, inventory
from preflight import check, resource_ledger


class PreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_main_sources_and_evidence_reproduce(self):
        self.assertEqual(self.baseline, inventory())

    def candidate(self):
        b = self.baseline["macros"]["S_P"]
        return dict(baseline_class="S_P", area=dict(outline_um2=b["outline_area_um2"],
            core_um2=b["core_area_um2"], functional_stdcell_um2=b["functional_stdcell_area_um2"],
            hardmacro_outline_um2=b["hardmacro_outline_area_um2"], physical_only_um2=0,
            source="final_odb", excludes_filler_tap_endcap_antenna=True),
            pins=dict(rtl_ports=[dict(name="all_bits_for_unit_test", width=965)], final_odb_signal_bits=965,
                exact_final_pin_readback=True, simultaneous_escape=True, native_pg_checked=True,
                halo_and_obstacles_checked=True), storage=[dict(usable_bytes=16384, physical_bytes=16384,
                    lvt_enabled=False, implementation="four 1RW banks", read_write_conflict_policy="exclusive phases")])

    def test_density_cannot_be_met_with_filler(self):
        c = self.candidate()
        self.assertEqual(check(c, self.baseline), [])
        c["area"]["functional_stdcell_um2"] -= 10000
        c["area"]["physical_only_um2"] += 10000
        self.assertTrue(any("falls below" in e for e in check(c, self.baseline)))

    def test_hierarchy_cannot_double_count_macro_internals(self):
        c = self.candidate()
        c["area"]["functional_stdcell_um2"] += c["area"]["hardmacro_outline_um2"]
        self.assertTrue(any("double counting" in e for e in check(c, self.baseline)))

    def test_width_and_lvt_are_real_resources(self):
        c = self.candidate()
        c["pins"]["rtl_ports"][0]["width"] -= 1
        c["storage"][0]["lvt_enabled"] = True
        errors = check(c, self.baseline)
        self.assertTrue(any("pin inventory" in e for e in errors))
        self.assertTrue(any("LVT" in e for e in errors))

    def test_storage_replacement_is_not_additive(self):
        r = resource_ledger()
        self.assertEqual(r["old"], 16384)
        self.assertEqual(r["down_s32_conservative"]["bytes"], 8128)
        self.assertEqual(r["down_mid_s32"]["bytes"], 7616)
        self.assertEqual(r["weight_replaces_double_b"]["with_x_bytes"], 14528)
        self.assertEqual(r["g_table"]["logical_bytes"], 1028)
        self.assertEqual(r["shared_pool"]["physical_bytes_minimum"], 32768)


if __name__ == "__main__":
    unittest.main()
