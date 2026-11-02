"""Parser/receiver controls. Actual native process controls live in native_control.py."""
import json
from pathlib import Path
import tempfile
import unittest

from audit import Invalid
from native_pair import receive, compare_native, native_log_diagnostics, signed_slack_diagnostic
from spef_inventory import inventory


def spef(resistance=1000):
    return f'''*SPEF "IEEE 1481-1998"
*DESIGN "qa_probe"
*DATE "fixed control"
*VENDOR "LLMHardwareDesign"
*PROGRAM "QA127"
*VERSION "1"
*DESIGN_FLOW "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*T_UNIT 1 NS
*C_UNIT 1 FF
*R_UNIT 1 OHM
*L_UNIT 1 UH
*NAME_MAP
*1 clk
*2 d
*3 q
*4 ff
*PORTS
*1 I
*2 I
*3 O
*D_NET *1 2
*CONN
*P *1 I
*I *4:CK I
*CAP
1 *1 1
2 *4:CK 1
*RES
1 *1 *4:CK 1
*END
*D_NET *2 3
*CONN
*P *2 I
*I *4:D I
*CAP
1 *2 1
2 *4:D 2
*RES
1 *2 *4:D {resistance}
*END
*D_NET *3 2
*CONN
*P *3 O
*I *4:Q O
*CAP
1 *3 1
2 *4:Q 1
*RES
1 *3 *4:Q 1
*END
'''


class SpefControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "probe.spef"

    def parse(self, text):
        self.path.write_text(text, encoding="utf-8")
        return inventory(self.path)

    def test_actual_record_inventory_and_unit_conversion(self):
        result = self.parse(spef())
        self.assertEqual(result["input_nets"]["d"]["resistance_sum_ohm"], 1000)
        self.assertEqual(result["input_nets"]["d"]["ground_cap_pf"], .003)
        self.assertEqual(result["nets"]["d"]["resistors"]["1"]["nodes"], ["d", "ff:D"])
        self.assertFalse(result["boundary_qualified"])

    def test_kohm_and_pf_conversion(self):
        result = self.parse(spef().replace("*R_UNIT 1 OHM", "*R_UNIT 1 KOHM").replace("*C_UNIT 1 FF", "*C_UNIT 1 PF"))
        self.assertEqual(result["input_nets"]["d"]["resistance_sum_ohm"], 1e6)
        self.assertEqual(result["input_nets"]["d"]["ground_cap_pf"], 3)

    def test_streamed_boundary_retention_preserves_actual_counts(self):
        full = self.parse(spef())
        boundary = inventory(self.path, retain_all=False)
        self.assertEqual(boundary["input_nets"], full["input_nets"])
        self.assertEqual(boundary["total_counts"], {"nets": 3, "resistors": 3, "capacitors": 6})
        self.assertEqual(set(boundary["nets"]), {"clk", "d"})

    def test_duplicate_nonretained_net_is_still_rejected(self):
        text = spef()
        text += text[text.index("*D_NET *3"):]
        self.path.write_text(text)
        with self.assertRaisesRegex(Invalid, "duplicate D_NET"):
            inventory(self.path, retain_all=False)

    def test_disconnected_input_sink(self):
        with self.assertRaisesRegex(Invalid, "disconnects sinks"):
            self.parse(spef().replace("1 *2 *4:D 1000", "1 *2 d:999 1000"))

    def test_floating_resistor_component(self):
        with self.assertRaisesRegex(Invalid, "floating input resistor"):
            self.parse(spef().replace("1 *2 *4:D 1000", "1 *2 *4:D 1000\n2 z:1 z:2 100"))

    def test_missing_input_net(self):
        text = spef()
        start, end = text.index("*D_NET *2"), text.index("*D_NET *3")
        with self.assertRaisesRegex(Invalid, "input-port D_NET"):
            self.parse(text[:start] + text[end:])

    def test_duplicate_resistor(self):
        with self.assertRaisesRegex(Invalid, "duplicate RC"):
            self.parse(spef().replace("1 *2 *4:D 1000", "1 *2 *4:D 1000\n1 *2 *4:D 1000"))

    def test_unknown_mapping(self):
        with self.assertRaisesRegex(Invalid, "unresolved"):
            self.parse(spef().replace("*4:D", "*99:D"))

    def test_nonfinite_negative_and_reduced_constructs(self):
        for text in (spef(float("nan")), spef(-1), spef().replace("*RES\n1 *2", "*R_NET\n1 *2")):
            with self.subTest(text=text[-70:]):
                with self.assertRaises(Invalid):
                    self.parse(text)

    def test_scaled_finite_quantity_overflow_rejected(self):
        with self.assertRaisesRegex(Invalid, "overflows"):
            self.parse(spef(1e308).replace("*R_UNIT 1 OHM", "*R_UNIT 1 KOHM"))


def reports(folder):
    (folder / "ports.tsv").write_text("clk\tinput\t.05\t.05\t.05\t.05\nd\tinput\t.01\t.01\t.01\t.01\nq\toutput\t.02\t.02\t.02\t.02\n")
    (folder / "endpoints.tsv").write_text("ff/D\t0\tinput\t1\t1\t.1\t.1\nq\t1\toutput\t2\t2\t.2\t.2\n")
    summary = {"time_unit_seconds": 1e-9, "capacitance_unit_farads": 1e-15,
               "check_setup": 1, "setup_violations": 0, "hold_violations": 0,
               "endpoint_count": 2, "observation_count": 8}
    (folder / "summary.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in summary.items()) +
                                        "capacitance\t0\t1\t10\nslew\t0\t.1\t.2\nfanout\t0\t1e30\t1e30\nclock\tcore\t1\t10\n")
    (folder / "observations.tsv").write_text("".join(
        f"{direction}\t{name}\t{edge}\t{analysis}\t{'d' if name=='d' else 'ff/CK'}\t{'ff/D' if name=='d' else 'q'}\t1\t2\t3\n"
        for direction, name in (("input", "d"), ("output", "q"))
        for edge in ("rise", "fall") for analysis in ("max", "min")))


class NativeReceiverControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.ports = {"clk": "input", "d": "input", "q": "output"}
        reports(self.folder)

    def test_complete_native_inventory(self):
        report = receive(self.folder, self.ports)
        self.assertEqual(len(report["observations"]), 8)
        result = compare_native(report, report, 1e-6, 1e-6)
        self.assertTrue(result["passed"])
        self.assertFalse(result["flat_abstract_boundary_qualified"])

    def test_missing_endpoint_rejected(self):
        path = self.folder / "endpoints.tsv"
        path.write_text(path.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(Invalid, "endpoint count"):
            receive(self.folder, self.ports)

    def test_missing_edge_observation_rejected(self):
        path = self.folder / "observations.tsv"
        path.write_text("\n".join(path.read_text().splitlines()[1:]) + "\n")
        with self.assertRaisesRegex(Invalid, "boundary coverage"):
            receive(self.folder, self.ports)

    def test_no_path_rejected(self):
        path = self.folder / "observations.tsv"
        path.write_text(path.read_text().replace("\td\tff/D\t", "\tNO_PATH\t-\t", 1))
        with self.assertRaisesRegex(Invalid, "path missing"):
            receive(self.folder, self.ports)

    def test_changed_units_rejected(self):
        path = self.folder / "summary.tsv"
        path.write_text(path.read_text().replace("1e-09", "1e-12"))
        with self.assertRaisesRegex(Invalid, "time units"):
            receive(self.folder, self.ports)

    def test_nonfinite_endpoints_are_visible(self):
        path = self.folder / "endpoints.tsv"
        path.write_text(path.read_text().replace("ff/D\t0\tinput\t1", "ff/D\t0\tinput\tINF"))
        report = receive(self.folder, self.ports)
        self.assertFalse(report["all_native_endpoint_slacks_finite"])
        self.assertIsNone(report["endpoints"]["ff/D"]["slacks_ns"][0])
        json.dumps(report, allow_nan=False)

    def test_native_measured_mismatch_is_reported(self):
        report = receive(self.folder, self.ports)
        altered = json.loads(json.dumps(report))
        altered["observations"][0]["slack_ns"] -= 1.1e-6
        result = compare_native(report, altered, 1e-6, 1e-6)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["mismatches"]), 1)

    def test_missing_spef_names_are_visible_despite_zero_process_exit(self):
        path = self.folder / "native.log"
        path.write_text("Warning 1648: instance diode:A not found.\nWarning 1650: net diode not found.\nError 1234: invalid library.\n")
        report = native_log_diagnostics(path)
        self.assertEqual(report["native_error_count"], 1)
        self.assertEqual(report["missing_spef_instance_or_net_messages"], 2)
        self.assertFalse(report["exact_source_annotation_binding_accepted"])

    def test_errors_with_code_after_colon_or_without_code_are_counted(self):
        path = self.folder / "native.log"
        path.write_text("Error: 1670 source.spef line 3, syntax error\nError: unnumbered failure\n")
        report = native_log_diagnostics(path)
        self.assertEqual(report["native_error_count"], 2)
        self.assertEqual(report["message_counts"]["Error 1670"], 1)
        self.assertEqual(report["message_counts"]["Error unnumbered"], 1)

    def test_optimistic_and_pessimistic_slack_directions_are_distinct(self):
        flat = receive(self.folder, self.ports)
        abstract = json.loads(json.dumps(flat))
        abstract["observations"][0]["slack_ns"] += .002
        abstract["observations"][1]["slack_ns"] -= .003
        result = signed_slack_diagnostic(flat, abstract, .001)
        self.assertEqual(result["optimistic_count"], 1)
        self.assertEqual(result["pessimistic_count"], 1)
        self.assertFalse(result["qualified_hard_macro"])

    def test_signed_comparison_rejects_missing_or_duplicate_coverage(self):
        flat = receive(self.folder, self.ports)
        for mutation in (lambda v: v["observations"].pop(), lambda v: v["observations"].append(v["observations"][0])):
            abstract = json.loads(json.dumps(flat))
            mutation(abstract)
            with self.assertRaises(Invalid):
                signed_slack_diagnostic(flat, abstract, .001)


if __name__ == "__main__":
    unittest.main()
