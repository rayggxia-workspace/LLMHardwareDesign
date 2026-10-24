"""Independent consumer, output containment, provenance and CLI replay tests."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from project.analysis.workload_mapping import core, examples
from project.analysis.workload_mapping.cli import new_output, output_build, verify_bundle
from project.analysis.workload_mapping.consumer import verify_mapping

ROOT = Path(__file__).resolve().parents[3]
TMP = ROOT/".local/tmp"
TMP.mkdir(parents=True, exist_ok=True)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cli-", dir=TMP)
        self.root = Path(self.temp.name).resolve()
        self.graph, self.blocks = examples.minimal()

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
        return subprocess.run([sys.executable,"-B","-m","project.analysis.workload_mapping",*args], cwd=ROOT, capture_output=True, text=True, env=env)

    def test_output_escape_and_existing_are_rejected(self):
        with self.assertRaises(ValueError):
            new_output(self.root, self.root.parent/"escaped")
        destination = self.root/"old"
        destination.mkdir()
        (destination/"keep").write_text("original")
        with self.assertRaises(ValueError):
            new_output(self.root, destination)
        self.assertEqual((destination/"keep").read_text(), "original")

    def test_actual_symlink_or_junction_escape(self):
        target = self.root/"actual"
        target.mkdir()
        link = self.root/"link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            p = subprocess.run(["cmd","/c","mklink","/J",str(link),str(target)], capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
        with self.assertRaises(ValueError):
            new_output(self.root, link/"run")
        self.assertFalse((target/"run").exists())

    def test_full_build_verify_and_replay(self):
        g, b = self.root/"g.json", self.root/"b.json"
        g.write_bytes(core.canonical(self.graph))
        b.write_bytes(core.canonical(self.blocks))
        first, second = self.root/"first", self.root/"second"
        p = self.run_cli("build","--graph",str(g),"--blocks",str(b),"--root",str(self.root),"--output-dir",str(first))
        self.assertEqual(p.returncode,0,p.stderr)
        p = self.run_cli("verify","--bundle",str(first))
        self.assertEqual(p.returncode,0,p.stderr)
        p = self.run_cli("replay","--bundle",str(first),"--root",str(self.root),"--output-dir",str(second))
        self.assertEqual(p.returncode,0,p.stderr)
        for name in ("mapping_request.json","resource_input.json","resource_report.json","summary.json"):
            self.assertEqual((first/name).read_bytes(),(second/name).read_bytes())
        summary = json.loads((first/"summary.json").read_text())
        self.assertEqual(summary["physical"]["status"], "not_executed")

    def test_rehashed_output_semantic_tamper_is_rejected(self):
        out = new_output(self.root,"run")
        output_build(self.graph,self.blocks,out)
        p = out/"mapping_request.json"
        mapping = core.read_json(p)
        mapping["communication"][0]["container_bytes"] += 1
        p.write_bytes(core.canonical(mapping))
        manifest = core.read_json(out/"manifest.json")
        manifest["files"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        (out/"manifest.json").write_bytes(core.canonical(manifest))
        with self.assertRaisesRegex(ValueError,"rebuild mismatch"):
            verify_bundle(out)
        with self.assertRaisesRegex(ValueError,"units"):
            verify_mapping(mapping)

    def test_independent_reader_rejects_ports_width_path_and_lifetime(self):
        mapping = core.build(self.graph,self.blocks)["mapping_request"]
        cases = []
        bad = copy.deepcopy(mapping)
        bad["links"][0]["destination_port"] = "absent"
        cases.append(bad)
        bad = copy.deepcopy(mapping)
        bad["resources"][0]["ports"][1]["width_bits"] = 64
        cases.append(bad)
        bad = copy.deepcopy(mapping)
        bad["communication"][0]["path"].reverse()
        cases.append(bad)
        bad = copy.deepcopy(mapping)
        bad["storage"]["peak_bytes"]["matrix"] -= 1
        cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad["id"]), self.assertRaises(ValueError):
                verify_mapping(bad)

    def test_input_version_changed_invalidates_old_manifest(self):
        out = new_output(self.root,"run")
        output_build(self.graph,self.blocks,out)
        blocks = core.read_json(out/"blocks.json")
        blocks["id"] += "-new-version"
        (out/"blocks.json").write_bytes(core.canonical(blocks))
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            verify_bundle(out)

    def test_duplicate_json_nonzero_and_failure_report(self):
        g,b = self.root/"g.json",self.root/"b.json"
        g.write_text('{"schema_version":"workload-mapping/1","schema_version":"typo"}')
        b.write_bytes(core.canonical(self.blocks))
        out = self.root/"bad"
        p = self.run_cli("build","--graph",str(g),"--blocks",str(b),"--root",str(self.root),"--output-dir",str(out))
        self.assertEqual(p.returncode,2)
        report = core.read_json(out/"summary.json")
        self.assertFalse(report["mapping_accepted"])
        self.assertIn("duplicate JSON key",report["error"])

    def test_network_forbidden_during_conversion_and_runtime_separation(self):
        out = new_output(self.root,"run")
        with patch("socket.socket.connect",side_effect=AssertionError("offline network prohibited")):
            output_build(self.graph,self.blocks,out)
            self.assertEqual(verify_bundle(out)["status"],"pass")
        manifest = core.read_json(out/"manifest.json")
        self.assertNotIn("runtime.json",manifest["files"])
        (out/"runtime.json").write_text('{"utc_epoch_seconds":0,"output":"changed"}')
        self.assertEqual(verify_bundle(out)["status"],"pass")


if __name__ == "__main__":
    unittest.main()
