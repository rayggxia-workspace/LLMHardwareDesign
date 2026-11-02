"""Synthetic integration controls for a source-bound native geometry receipt."""
import json
from pathlib import Path
import tempfile
import unittest

from audit import Invalid, file_sha
from receive_occupancy import receive
from test_audit import Fixture


class OccupancyReceiptControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "candidate").mkdir()
        self.f = Fixture(self.root / "candidate")
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.output = self.root / "result"
        task, src = "/runs/occupancy", "/runs/source/src/"
        self.origins = {"receipt": task+"/receipt.json", "report": task+"/native-qa-occupancy.json",
                        "summary": task+"/occupancy-summary.tsv", "geometry": task+"/source-occupancy.tsv",
                        "wrapper": task+"/readonly-occupancy.tcl", "native_log": task+"/native-occupancy.log",
                        "producer": src+"project/experiments/block_v1/native_qa_occupancy.py",
                        "helper": src+"project/experiments/block_v1/odb_geometry.tcl",
                        "collector": src+"project/experiments/block_v1/qa127_pinned/source_occupancy.tcl"}
        for role in ("producer", "helper", "collector", "native_log"):
            (self.evidence / role).write_text("synthetic "+role)
        (self.evidence / "geometry").write_text("# block-v1-odb-geometry/1 dbu_per_um=2000\n# NET n1 64\nn1\tmetal1\twire\t0\t0\t10\t10\n")
        (self.evidence / "summary").write_text("dbu_per_um\t2000\nnative_instances\t1\nnative_master_obstruction_boxes\t0\n")
        odb = self.f.items["final_odb"]["origin"]
        wrapper = "set_thread_count 1\nset ::env(BV1QA_ODB) {"+odb+"}\n"
        wrapper += "set ::env(BV1QA_GEOMETRY_HELPER) {"+self.origins["helper"]+"}\nsource {"+self.origins["collector"]+"}\n"
        (self.evidence / "wrapper").write_text(wrapper)
        collector_hash = file_sha(self.evidence / "collector")
        self.report = {"schema": "block-v1-qa127-native-occupancy/1", "passed": True, "policy": "A",
                       "source_odb": odb, "source_odb_sha256": self.f.digest("final_odb"),
                       "inputs": {self.origins[r]: file_sha(self.evidence / r) for r in ("helper", "collector")},
                       "pinned_origin": {"repository": "rayggxia-workspace/LLMHardwareDesign", "source_commit": "c"*40,
                                         "source_path": "project/experiments/block_v1/macro_boundary_qa/source_occupancy.tcl", "sha256": collector_hash},
                       "native_summary": {"dbu_per_um": 2000, "native_instances": 1, "native_master_obstruction_boxes": 0}}
        for role in ("physical_receipt", "physical_report"):
            self.report["inputs"][self.f.items[role]["origin"]] = self.f.digest(role)
        self.producer = {"passed": True, "cpus": 1, "mode": "native-qa-occupancy-a",
                         "commands": [{"returncode": 0}], "tool_hashes": {"openroad": "a"*64}, "outputs": {},
                         "inputs": {"project/experiments/block_v1/"+name: file_sha(self.evidence / role)
                                    for role, name in (("producer", "native_qa_occupancy.py"), ("helper", "odb_geometry.tcl"), ("collector", "qa127_pinned/source_occupancy.tcl"))}}
        self.expected_collector = {"source_commit": "c"*40, "sha256": collector_hash}
        self.seal()

    def seal(self):
        p = self.evidence
        self.report["occupancy"] = {"path": self.origins["geometry"], "sha256": file_sha(p/"geometry"), "bytes": (p/"geometry").stat().st_size}
        (p/"report").write_text(json.dumps(self.report))
        for role in ("report", "summary", "geometry", "wrapper", "native_log"):
            self.producer["outputs"][self.origins[role].rsplit("/", 1)[-1]] = file_sha(p/role)
        (p/"receipt").write_text(json.dumps(self.producer))
        manifest = {"schema": "block-v1-native-occupancy-evidence/1", "candidate_index_sha256": file_sha(self.f.index_path),
                    "expected_collector": self.expected_collector,
                    "files": {role: {"path": role, "origin": original, "sha256": file_sha(p/role)} for role, original in self.origins.items()}}
        (p/"evidence.json").write_text(json.dumps(manifest))

    def run_receiver(self):
        return receive(self.f.index_path, self.evidence/"evidence.json", self.output)

    def test_bound_synthetic_export_is_checked_without_qualification(self):
        result = self.run_receiver()
        self.assertTrue(result["passed"])
        self.assertEqual(result["checked_source_metal_rectangles"], 1)
        self.assertFalse(result["qualified_hard_macro"])

    def test_different_source_odb_rejected_despite_resealed_producer(self):
        self.report["source_odb_sha256"] = "0"*64
        self.seal()
        with self.assertRaisesRegex(Invalid, "source ODB mismatch"):
            self.run_receiver()

    def test_wrong_native_wrapper_rejected_despite_resealed_producer(self):
        p = self.evidence/"wrapper"
        p.write_text(p.read_text().replace("set_thread_count 1", "set_thread_count 2"))
        self.seal()
        with self.assertRaisesRegex(Invalid, "wrapper semantics"):
            self.run_receiver()

    def test_native_success_does_not_hide_uncovered_geometry(self):
        p = self.evidence/"geometry"
        p.write_text(p.read_text().replace("\t10\t10", "\t1001\t10"))
        self.seal()
        result = self.run_receiver()
        self.assertFalse(result["passed"])
        self.assertEqual(result["uncovered_count"], 1)


if __name__ == "__main__":
    unittest.main()
