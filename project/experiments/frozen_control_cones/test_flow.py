"""Tests use actual saved native exports; mutations are confined to TMPDIR."""
import copy
import json
import os
import csv
import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path
import flow

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE/"example.json").read_text())
NATIVE = HERE/"fixtures/native"


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="control-cone-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"native"
        shutil.copytree(NATIVE, self.root)
        self.cfg = copy.deepcopy(CFG)

    def validate(self, label="opentpu", case=None):
        return flow.validate(self.root/"base/native", self.root/label/"native",
                             self.cfg, case or self.cfg["cases"][0])

    def test_both_native_export_cases(self):
        for case, label in zip(self.cfg["cases"], ["opentpu", "llaccel"]):
            result = self.validate(label, case)
            self.assertEqual(result["status"], "PASS_SCOPED_REPLAY", result)

    def test_real_removed_via_rejected(self):
        result = self.validate("negative_open")
        self.assertEqual(result["status"], "REJECTED", result)
        self.assertIn(result["reason"], ["OPEN", "PIN_ACCESS"])

    def test_real_top_short_rejected(self):
        self.assertEqual(self.validate("negative_short")["reason"], "SHORT")

    def test_connected_other_function_rejected(self):
        self.assertEqual(self.validate("llaccel")["reason"], "FUNCTION_MISMATCH")

    def test_fixed_instance_move_rejected(self):
        path = self.root/"opentpu/native.instances.tsv"
        path.write_text(path.read_text().replace("20520", "20530"))
        self.assertEqual(self.validate()["reason"], "FROZEN_INSTANCE")

    def test_changed_instance_and_port_names(self):
        replacements = [("not_b", "different_inverter"),
                        ("and_gate", "different_gate"),
                        ("PIN/a", "PIN/x"), ("PIN/b", "PIN/z"), ("PIN/y", "PIN/q")]
        for path in self.root.rglob("*"):
            if path.is_file():
                text = path.read_text()
                for old, new in replacements:
                    text = text.replace(old, new)
                path.write_text(text)
        self.cfg["input_ports"] = ["PIN/x", "PIN/z"]
        self.cfg["output_ports"] = ["PIN/q"]
        result = self.validate()
        self.assertEqual(result["status"], "PASS_SCOPED_REPLAY", result)

    def test_input_order_and_truth_table_are_parameters(self):
        self.cfg["input_ports"].reverse()
        self.cfg["cases"][1]["expected"] = [[0], [1], [0], [0]]
        result = self.validate("llaccel", self.cfg["cases"][1])
        self.assertEqual(result["status"], "PASS_SCOPED_REPLAY", result)

    def test_unknown_cell_rejected(self):
        del self.cfg["cells"]["INV_X1"]
        self.assertEqual(self.validate()["reason"], "UNSUPPORTED_CELL")

    def test_wrong_model_table_rejected_by_reference(self):
        self.cfg["cells"]["AND2_X1"]["truth_table"] = [0, 1, 1, 1]
        self.assertEqual(self.validate()["reason"], "FUNCTION_MISMATCH")

    def test_enumeration_budget_rejected(self):
        self.cfg["maximum_exhaustive_inputs"] = 1
        self.assertEqual(self.validate()["reason"], "ENUMERATION_LIMIT")

    def test_new_lower_metal_rejected(self):
        path = self.root/"opentpu/native.odb_export.def"
        text = path.read_text()
        # Add an isolated new M10 wire to a net, before the first route.
        marker = "+ ROUTED"
        self.assertIn(marker, text)
        # SPECIALNETS comes first; insert into a signal NETS route instead.
        pos = text.index("\nNETS ")
        text = text[:pos] + text[pos:].replace(
            marker, "+ ROUTED metal10 ( 200000 100000 ) ( 210000 100000 ) NEW", 1)
        path.write_text(text)
        self.assertEqual(self.validate()["reason"], "LOWER_FOOTPRINT_ADDED")

    def test_power_assignment_change_rejected(self):
        path = self.root/"opentpu/native.terminals.tsv"
        text = path.read_text().replace("not_b/VDD\tVDD", "not_b/VDD\tVSS")
        path.write_text(text)
        self.assertEqual(self.validate()["reason"], "FROZEN_POWER")

    def test_translated_native_coordinates(self):
        # Translate route anchors and native absolute geometry together.
        # Via definitions stay relative and therefore must not move.
        for label in ["base", "opentpu"]:
            folder = self.root/label
            for suffix, columns in [
                ("instances.tsv", ["ox", "oy"]),
                ("terminals.tsv", ["x1", "y1", "x2", "y2"]),
                ("obstructions.tsv", ["x1", "y1", "x2", "y2"])]:
                path = folder/("native."+suffix)
                with path.open() as stream:
                    reader = csv.DictReader(stream, delimiter="\t")
                    fields, records = reader.fieldnames, list(reader)
                for record in records:
                    for key in columns:
                        record[key] = str(int(record[key])+20)
                with path.open("w") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t",
                                            lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(records)
            path = folder/"native.odb_export.def"
            pattern = r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)"
            def move(match):
                values = [str(int(v)+20) if v != "*" else v
                          for v in match.groups()[:2]]
                if match[3] is not None:
                    values.append(match[3])  # endpoint extension is a length
                return "( "+" ".join(values)+" )"
            path.write_text(re.sub(pattern, move, path.read_text()))
        result = self.validate()
        self.assertEqual(result["status"], "PASS_SCOPED_REPLAY", result)

    def test_parser_rejects_diagonal(self):
        with self.assertRaises(ValueError):
            flow.g.segment([0, 0, None], [10, 10, None], 2)

    def test_rectangular_overlap_rejected(self):
        path = self.root/"opentpu/native.instances.tsv"
        # Exercise overlap independently: common-base move would otherwise
        # correctly be rejected earlier as a freeze violation.
        path.write_text(path.read_text().replace("80180", "20520"))
        with self.assertRaises(flow.Rejected) as caught:
            flow.check_overlap(self.root/"opentpu/native", self.cfg)
        self.assertEqual(caught.exception.code, "CELL_OVERLAP")


if __name__ == "__main__":
    unittest.main(verbosity=2)
