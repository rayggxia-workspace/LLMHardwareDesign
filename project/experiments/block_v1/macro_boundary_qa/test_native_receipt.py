"""Synthetic subprocess controls for native evidence binding, not EDA results."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from audit import Invalid, file_sha
from native_pair import run, verify
from test_native import reports, spef


class NativeReceiptControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        inputs = self.root / "inputs"
        inputs.mkdir()
        self.executable = inputs / "fake-sta"
        self.executable.write_text("synthetic subprocess only")
        files = {}
        for role in ("flat_verilog", "flat_spef", "sdc", "abstract_verilog", "macro_lib", "base_lib_0"):
            path = inputs / role
            path.write_text(spef() if role == "flat_spef" else f"synthetic {role}")
            files[role] = {"path": str(path), "sha256": file_sha(path)}
        self.request = {"schema": "block-v1-native-boundary-request/1", "evidence_kind": "native-control",
                        "abstract_parent_interconnect": "ideal", "flat_top": "qa_probe", "abstract_top": "qa_wrapper",
                        "expected_ports": {"clk": "input", "d": "input", "q": "output"},
                        "time_tolerance_ns": .001, "slew_tolerance_ns": .001, "files": files}
        self.request_path = inputs / "request.json"
        self.request_path.write_text(json.dumps(self.request))
        self.output = self.root / "result"

    def execute(self, warning="", failure=0):
        def synthetic_process(argv, cwd, env, stdout, **kwargs):
            reports(Path(cwd))
            stdout.write(warning)
            return SimpleNamespace(returncode=failure)
        # This fixture never launches Tcl; Windows temporary paths therefore
        # need no native Tcl serialization. Actual native controls run on Linux.
        with patch("native_pair.subprocess.run", side_effect=synthetic_process), patch("native_pair.tcl_list", return_value="synthetic-library-list"):
            return run(self.request_path, self.output, self.executable)

    def rehash_output(self, relative):
        path = self.output / "receipt.json"
        receipt = json.loads(path.read_text())
        receipt["outputs"][relative] = file_sha(self.output / relative)
        path.write_text(json.dumps(receipt))

    def test_recompute_passes_bound_synthetic_process_reports(self):
        self.assertTrue(self.execute()["passed"])
        self.assertTrue(verify(self.output, self.request_path)["native_measurement_binding_passed"])

    def test_changed_measured_tsv_is_rejected(self):
        self.execute()
        path = self.output / "flat/observations.tsv"
        path.write_text(path.read_text().replace("\t1\t2\t3", "\t.99\t2\t3", 1))
        with self.assertRaisesRegex(Invalid, "output receipt binding"):
            verify(self.output, self.request_path)

    def test_rehashed_forged_summary_is_still_recomputed(self):
        self.execute()
        path = self.output / "native-pair-report.json"
        report = json.loads(path.read_text())
        report["differences"][0]["slack_absolute_difference_ns"] = .1
        path.write_text(json.dumps(report))
        self.rehash_output("native-pair-report.json")
        with self.assertRaisesRegex(Invalid, "saved comparison disagrees"):
            verify(self.output, self.request_path)

    def test_rehashed_collector_snapshot_must_match_executed_hash(self):
        self.execute()
        path = self.output / "provenance/measure_native.tcl"
        path.write_text("synthetic forged collector")
        self.rehash_output("provenance/measure_native.tcl")
        with self.assertRaisesRegex(Invalid, "executed code binding"):
            verify(self.output, self.request_path)

    def test_tool_changed_after_execution_is_rejected(self):
        self.execute()
        self.executable.write_text("synthetic replacement")
        with self.assertRaisesRegex(Invalid, "executable binding"):
            verify(self.output, self.request_path)

    def test_zero_exit_with_missing_spef_names_is_not_an_accepted_context(self):
        result = self.execute("Warning 1650: net missing not found.\n")
        self.assertFalse(result["passed"])
        self.assertFalse(result["measurement_context_accepted"])
        self.assertTrue(json.loads((self.output / "receipt.json").read_text())["passed"])
        received = verify(self.output, self.request_path)
        self.assertFalse(received["models_match_within_declared_diagnostic_tolerances"])

    def test_failed_process_keeps_failed_receipt_and_logs(self):
        with self.assertRaisesRegex(Invalid, "process failed"):
            self.execute("synthetic failure", failure=1)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertFalse(receipt["passed"])
        self.assertTrue((self.output / "flat/native.log").exists())


if __name__ == "__main__":
    unittest.main()
