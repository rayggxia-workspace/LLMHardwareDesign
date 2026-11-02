"""Synthetic positive/negative controls, not physical qualification results."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


MODULE = Path(__file__).with_name("audit.py")
SPEC = importlib.util.spec_from_file_location("macro_boundary_audit", MODULE)
qa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qa)
sys.modules["audit"] = qa
PACK_SPEC = importlib.util.spec_from_file_location("macro_boundary_pack", MODULE.with_name("pack_native.py"))
packer = importlib.util.module_from_spec(PACK_SPEC)
PACK_SPEC.loader.exec_module(packer)


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


class Fixture:
    def __init__(self, root):
        self.root = Path(root)
        self.items = {}
        self.owned = {}
        self.index = {"schema": "block-v1-macro-qa-bundle/1", "evidence_kind": "synthetic",
                      "top": "shared109", "policy": "A", "files": self.items}
        self.receipts = {}
        for i, role in enumerate(("source_receipt", "physical_receipt", "view_receipt", "prepare_receipt"), 1):
            self.receipts[role] = {"passed": True, "source_commit": str(i)*40,
                                   "tool_hashes": {"openroad": "a"*64}, "outputs": {}}
            self.put(role, f"/runs/{role}/receipt.json", self.receipts[role])
        prefix = "flow/results/nangate45/bv1_shared109_A/base"
        for role, suffix in qa.FINALS.items():
            self.output(role, "source_receipt", f"{prefix}/6_final.{suffix}", f"synthetic {suffix}\n")
        self.output("gds", "physical_receipt", f"gds-{prefix}/6_final.gds", "synthetic gds\n")
        self.put("pipeline", "/repo/native_pipeline.json", {"candidate_run": "source"})
        self.put("budget", "/repo/physical-budget.json", {"leaves": {"shared109": {"die_um": [2000, 2000]}}})
        self.receipts["view_receipt"]["inputs"] = {
            "project/experiments/block_v1/physical-budget.json": self.digest("budget"),
            "project/experiments/block_v1/native_pipeline.json": self.digest("pipeline"),
            "project/experiments/block_v1/native_views.py": "d"*64,
            "project/experiments/block_v1/native_views.tcl": "e"*64,
            "project/experiments/block_v1/native_lib_pins.tcl": "f"*64}
        pins = [{"pin": n, "direction": d, "xy_um": [x, 1], "size_um": [.2, .2]}
                for n, d, x in (("clk", "input", 1), ("d[0]", "input", 2),
                                ("d[1]", "input", 3), ("q", "output", 4))]
        self.output("pins", "prepare_receipt", "shared109-A/pins.json", {"pins": pins})
        lef = ["width\t4000000", "height\t4000000"]
        for pin in pins:
            name, x = pin["pin"], pin["xy_um"][0]*2000
            lef += [f"term\t{name}\t{pin['direction'].upper()}\tSIGNAL",
                    f"box\t{name}\tmetal10\t{x-200}\t1800\t{x+200}\t2200"]
        lef += ["term\tVDD\tINOUT\tPOWER", "box\tVDD\tmetal1\t0\t0\t100\t100",
                "term\tVSS\tINOUT\tGROUND", "box\tVSS\tmetal1\t200\t0\t300\t100"]
        lef += [f"obstruction\tmetal{i}\t0\t0\t1000\t1000" for i in range(1, 11)]
        outputs = {"lef_interface": "\n".join(lef)+"\n",
                   "lib_interface": "\n".join(f"BV1_shared109_A/shared109/{p['pin']}\t{p['direction']}" for p in pins)+"\n",
                   "lib_buses": "BV1_shared109_A/shared109/d\tinput\td[0] d[1]\n",
                   "source_pg": "VDD\tmetal1\t0\t0\t100\t100\nVSS\tmetal1\t200\t0\t300\t100\n",
                   "lib": "synthetic liberty\n", "lef": "synthetic lef\n"}
        for role, value in outputs.items():
            self.output(role, "view_receipt", qa.VIEW_OUTPUTS[role], value)
        physical = {"schema": "block-v1-native-physical-receiver/1", "passed": True,
                    "top": "shared109", "policy": "A", "pipeline": "native_pipeline.json",
                    "source": "/runs/source_receipt", "source_receipt_sha256": self.digest("source_receipt"),
                    "checks": {k: True for k in qa.PHYSICAL_GATES},
                    "historical_input_contract": False, "rc_coverage_qualified": True,
                    "mapped_to_final_lec": {"passed": True}, "independent_drc_items": 0,
                    "gds_sha256": self.digest("gds")}
        self.output("physical_report", "physical_receipt", "native-physical-receiver.json", physical)
        self.view = {"schema": "block-v1-native-view-generation/1", "passed": True,
                     "top": "shared109", "policy": "A", "pipeline": "native_pipeline.json",
                     "pipeline_file_sha256": self.digest("pipeline"),
                     "generator_sha256": "d"*64, "readback_script_sha256": "e"*64,
                     "lib_interface_script_sha256": "f"*64,
                     "source": "/runs/source_receipt", "source_receipt_sha256": self.digest("source_receipt"),
                     "physical_receiver": "/runs/physical_receipt",
                     "physical_receiver_sha256": self.digest("physical_report"),
                     "physical_receiver_receipt_sha256": self.digest("physical_receipt"),
                     "typed_bus_metadata_sha256": self.digest("lib_buses"),
                     "inputs": {self.items[r]["origin"]: self.digest(r) for r in qa.FINALS},
                     "views": {f"candidate.{r}": {"path": self.items[r]["origin"], "sha256": self.digest(r)} for r in ("lib", "lef")},
                     "native_gds": {"path": self.items["gds"]["origin"], "sha256": self.digest("gds")}}
        self.output("view_report", "view_receipt", "native-view-generation.json", self.view)
        self.save()

    def digest(self, role):
        return self.items[role]["sha256"]

    def put(self, role, original, value):
        data = value.encode() if isinstance(value, str) else encoded(value)
        path = self.root / role
        path.write_bytes(data)
        self.items[role] = {"path": role, "origin": original, "sha256": qa.sha(data)}

    def output(self, role, receipt_role, relative, value):
        self.put(role, f"/runs/{receipt_role}/{relative}", value)
        self.owned[role] = (receipt_role, relative)
        self.receipts[receipt_role]["outputs"][relative] = self.digest(role)
        self.put(receipt_role, f"/runs/{receipt_role}/receipt.json", self.receipts[receipt_role])

    def change(self, role, value, producer=False):
        original = self.items[role]["origin"]
        if producer:
            receipt_role, relative = self.owned[role]
            self.output(role, receipt_role, relative, value)
        else:
            self.put(role, original, value)
        self.save()

    def bind_budget(self):
        self.receipts["view_receipt"]["inputs"]["project/experiments/block_v1/physical-budget.json"] = self.digest("budget")
        self.put("view_receipt", "/runs/view_receipt/receipt.json", self.receipts["view_receipt"])
        self.save()

    def save(self):
        self.index_path = self.root / "index.json"
        self.index_path.write_bytes(encoded(self.index))

    def text(self, role):
        return (self.root / role).read_text()

    def obj(self, role):
        return qa.load_json(self.text(role))

    def bundle(self):
        return qa.Bundle(self.index_path)


def comparison_fixture():
    context = {"source_receipt_sha256": "a"*64, "final_sdc_sha256": "b"*64,
               "corner": "typical", "clock_ns": 10, "uncertainty_ns": .1, "clock_transition_ns": .05,
               "input_delay_max_ns": 2, "input_delay_min_ns": .2,
               "output_delay_max_ns": 2, "output_delay_min_ns": .2,
               "input_driver": {"cell": "BUF_X2", "pin": "Z"}, "output_load_pf": .002}
    spec = {"schema": "block-v1-boundary-comparison-spec/1", "measurements": ["clk->q/rise"],
            "units": qa.METRIC_UNITS, "absolute_tolerance": {k: 1e-6 for k in qa.METRIC_UNITS},
            "context": context, "parasitic_components": {
                "input0": {"kind": "input_wire_resistance", "unit": "ohm", "absolute_tolerance": .001},
                "wire0": {"kind": "ground_capacitance", "unit": "pF", "absolute_tolerance": 1e-6}}}
    flat = {"schema": "block-v1-boundary-measurements/1", "view": "flat", "spec_sha256": qa.sha(encoded(spec)),
            "context": deepcopy(context), "measurements": {"clk->q/rise": {k: .1 for k in qa.METRIC_UNITS}},
            "parasitics": {key: {"segments": ["segment0", "segment1"],
                                  "owners": {"segment0": ["macro"], "segment1": ["parent"]},
                                  "value": .1} for key in spec["parasitic_components"]}}
    abstract = deepcopy(flat)
    abstract["view"] = "abstract"
    return spec, flat, abstract


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(self.temp.name)

    def test_full_synthetic_audit_does_not_qualify(self):
        report = qa.audit(self.f.index_path)
        self.assertTrue(report["passed"])
        self.assertFalse(report["qualified_hard_macro"])
        self.assertFalse(report["flat_abstract_boundary_qualified"])
        self.assertFalse(report["interface"]["obstruction_geometry_coverage_qualified"])
        self.assertFalse(report["comparison"]["passed"])

    def test_different_stage_commits_are_allowed(self):
        result = qa.audit_source(self.f.bundle())
        self.assertEqual(len(set(result["stage_commits"].values())), 4)

    def test_tampered_file(self):
        (self.f.root / "final_spef").write_text("changed")
        with self.assertRaisesRegex(qa.Invalid, "hash mismatch"):
            self.f.bundle()

    def test_rehashed_file_without_producer_update(self):
        self.f.change("final_spef", "different parasitics")
        with self.assertRaisesRegex(qa.Invalid, "producer output mismatch"):
            qa.audit_source(self.f.bundle())

    def test_mixed_source(self):
        self.f.view["source_receipt_sha256"] = "0"*64
        self.f.change("view_report", self.f.view, producer=True)
        with self.assertRaisesRegex(qa.Invalid, "mixed source receipt"):
            qa.audit_source(self.f.bundle())

    def test_budget_not_from_exporter_inputs(self):
        self.f.change("budget", {"leaves": {"shared109": {"die_um": [100, 100]}}})
        with self.assertRaisesRegex(qa.Invalid, "configuration binding: budget"):
            qa.audit_source(self.f.bundle())

    def test_mixed_origin_even_with_matching_hash(self):
        self.f.index["files"]["final_v"]["origin"] = "/different/6_final.v"
        self.f.save()
        with self.assertRaisesRegex(qa.Invalid, "producer origin mismatch"):
            qa.audit_source(self.f.bundle())

    def test_unknown_failed_gate_and_missing_gate(self):
        for mode in ("missing", "new failed gate"):
            with self.subTest(mode=mode):
                physical = self.f.obj("physical_report")
                if mode == "missing":
                    physical["checks"].pop("timing")
                else:
                    physical["checks"]["timing"] = True
                    physical["checks"]["fresh_native_short_gate"] = False
                self.f.change("physical_report", physical, producer=True)
                self.f.view.update(physical_receiver_sha256=self.f.digest("physical_report"),
                                   physical_receiver_receipt_sha256=self.f.digest("physical_receipt"))
                self.f.change("view_report", self.f.view, producer=True)
                with self.assertRaisesRegex(qa.Invalid, "physical gates"):
                    qa.audit_source(self.f.bundle())

    def test_path_escape_and_origin_alias(self):
        for path in ("../outside", "C:/Windows/win.ini", "a\\b"):
            with self.subTest(path=path):
                self.f.items["final_v"]["path"] = path
                self.f.save()
                with self.assertRaises((qa.Invalid, OSError)):
                    self.f.bundle()

    def test_duplicate_json_and_nan(self):
        for value in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(qa.Invalid):
                qa.load_json(value)

    def test_partial_comparison_is_rejected(self):
        spec, _, _ = comparison_fixture()
        self.f.put("comparison_spec", "/comparison/spec.json", spec)
        self.f.save()
        with self.assertRaisesRegex(qa.Invalid, "partial comparison"):
            qa.audit(self.f.index_path)

    def test_complete_comparison_is_bound_to_source_and_budget(self):
        spec, flat, abstract = comparison_fixture()
        spec["context"].update(source_receipt_sha256=self.f.digest("source_receipt"),
                               final_sdc_sha256=self.f.digest("final_sdc"))
        budget = self.f.obj("budget")
        budget.update({key: spec["context"][key] for key in qa.BUDGET_CONTEXT})
        self.f.change("budget", budget)
        self.f.bind_budget()
        for report in (flat, abstract):
            report["context"] = deepcopy(spec["context"])
            report["spec_sha256"] = qa.sha(encoded(spec))
        for role, value in (("comparison_spec", spec), ("flat_measurements", flat),
                            ("abstract_measurements", abstract)):
            self.f.put(role, f"/comparison/{role}.json", value)
        self.f.save()
        result = qa.audit(self.f.index_path)
        self.assertTrue(result["comparison"]["passed"])
        self.assertFalse(result["flat_abstract_boundary_qualified"])
        budget["output_load_pf"] *= 2
        self.f.change("budget", budget)
        self.f.bind_budget()
        with self.assertRaisesRegex(qa.Invalid, "physical budget"):
            qa.audit(self.f.index_path)

    def test_concurrent_change_detected(self):
        bundle = self.f.bundle()
        (self.f.root / "lib").write_text("modified after snapshot")
        with self.assertRaisesRegex(qa.Invalid, "changed during audit"):
            bundle.unchanged()

    def test_cli_failure_is_json_and_nonzero(self):
        (self.f.root / "lib").write_text("tampered")
        result = subprocess.run([sys.executable, "-B", str(MODULE), str(self.f.index_path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["passed"])
        self.assertEqual(result.stderr, "")


class InterfaceControls(unittest.TestCase):
    setUp = SourceTests.setUp

    def reject(self, role, old, new, message):
        self.f.change(role, self.f.text(role).replace(old, new))
        with self.assertRaisesRegex(qa.Invalid, message):
            qa.audit_interface(self.f.bundle())

    def test_wrong_direction(self):
        self.reject("lib_interface", "d[0]\tinput", "d[0]\toutput", "port/direction")

    def test_duplicate_port(self):
        self.f.change("lib_interface", self.f.text("lib_interface") + "BV1_shared109_A/shared109/q\toutput\n")
        with self.assertRaisesRegex(qa.Invalid, "duplicate Liberty"):
            qa.audit_interface(self.f.bundle())

    def test_missing_bus_member(self):
        self.reject("lib_buses", "d[0] d[1]", "d[0]", "bus membership")

    def test_wrong_bus_scope(self):
        self.reject("lib_buses", "BV1_shared109_A", "wrong_library", "scoped identity")

    def test_wrong_pin_layer(self):
        self.reject("lef_interface", "box\tq\tmetal10", "box\tq\tmetal9", "M10 pin geometry")

    def test_wrong_pg_geometry(self):
        self.reject("source_pg", "100\t100", "110\t100", "PG geometry")

    def test_custom_layer_obstruction(self):
        self.reject("lef_interface", "obstruction\tmetal1\t", "obstruction\tmetal11\t", "OBS layer")

    def test_orphan_pin_geometry(self):
        self.f.change("lef_interface", self.f.text("lef_interface") + "box\torphan\tmetal10\t0\t0\t100\t100\n")
        with self.assertRaisesRegex(qa.Invalid, "orphan"):
            qa.audit_interface(self.f.bundle())

    def test_tiny_obstructions_remain_unqualified(self):
        result = qa.audit_interface(self.f.bundle())
        self.assertTrue(result["passed"])
        self.assertFalse(result["obstruction_geometry_coverage_qualified"])


class PackControls(unittest.TestCase):
    setUp = SourceTests.setUp

    def test_portable_copy_and_existing_output_rejected(self):
        destination = tempfile.TemporaryDirectory()
        self.addCleanup(destination.cleanup)
        output = Path(destination.name) / "bundle"
        paths = {role: self.f.root / item["path"] for role, item in self.f.items.items()}
        origins = {role: item["origin"] for role, item in self.f.items.items()}
        result = packer.pack("shared109", "A", paths, output, "synthetic", origins)
        self.assertTrue(result["passed"])
        self.assertFalse(result["qualified_hard_macro"])
        self.assertEqual(qa.file_sha(output / "final_odb"), self.f.digest("final_odb"))
        with self.assertRaises(FileExistsError):
            packer.pack("shared109", "A", paths, output, "synthetic", origins)

    def test_pack_inside_source_rejected(self):
        paths = {role: self.f.root / item["path"] for role, item in self.f.items.items()}
        with self.assertRaisesRegex(qa.Invalid, "outside all producer"):
            packer.pack("shared109", "A", paths, self.f.root / "bundle", "synthetic")


class ComparisonControls(unittest.TestCase):
    def setUp(self):
        self.spec, self.flat, self.abstract = comparison_fixture()

    def compare(self):
        return qa.compare(self.spec, self.flat, self.abstract, qa.sha(encoded(self.spec)))

    def test_positive_remains_diagnostic(self):
        result = self.compare()
        self.assertTrue(result["passed"])
        self.assertFalse(result["native_extraction_proof_qualified"])

    def test_small_mismatch_not_rounded_away(self):
        self.abstract["measurements"]["clk->q/rise"]["hold_slack_ns"] += 1.1e-6
        with self.assertRaisesRegex(qa.Invalid, "timing mismatch"):
            self.compare()

    def test_missing_endpoint(self):
        self.abstract["measurements"] = {}
        with self.assertRaisesRegex(qa.Invalid, "timing measurement"):
            self.compare()

    def test_nonfinite(self):
        self.flat["measurements"]["clk->q/rise"]["cap_pf"] = float("inf")
        with self.assertRaisesRegex(qa.Invalid, "finite number"):
            self.compare()

    def test_changed_environment(self):
        self.abstract["context"]["input_driver"]["cell"] = "BUF_X4"
        with self.assertRaisesRegex(qa.Invalid, "environment"):
            self.compare()

    def test_changed_spec_or_units(self):
        self.spec["units"] = {**qa.METRIC_UNITS, "cap_pf": "fF"}
        with self.assertRaisesRegex(qa.Invalid, "units"):
            self.compare()

    def test_posthoc_tolerance_change(self):
        self.spec["absolute_tolerance"]["cap_pf"] = 1
        with self.assertRaisesRegex(qa.Invalid, "spec/environment"):
            self.compare()

    def test_omitted_and_double_counted_rc(self):
        for owners in ([], ["macro", "parent"]):
            with self.subTest(owners=owners):
                self.abstract["parasitics"]["input0"]["owners"]["segment0"] = owners
                with self.assertRaisesRegex(qa.Invalid, "double-counted"):
                    self.compare()

    def test_different_segment_inventory(self):
        item = self.abstract["parasitics"]["input0"]
        item["segments"] = ["other"]
        item["owners"] = {"other": ["macro"]}
        with self.assertRaisesRegex(qa.Invalid, "different physical RC"):
            self.compare()

    def test_missing_input_wire_resistance(self):
        self.spec["parasitic_components"].pop("input0")
        with self.assertRaisesRegex(qa.Invalid, "input wire resistance"):
            self.compare()

    def test_rc_value_mismatch(self):
        self.abstract["parasitics"]["input0"]["value"] += .002
        with self.assertRaisesRegex(qa.Invalid, "RC mismatch"):
            self.compare()


if __name__ == "__main__":
    unittest.main()
