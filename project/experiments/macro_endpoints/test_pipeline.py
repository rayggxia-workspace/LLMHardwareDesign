"""Capture-integrity and hierarchy-preservation tests; no SSH is performed."""
import base64
import copy
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from common import CONFIG, HERE, ROOT, check_config, file_index, json_bytes, load_snapshot, sha
from capture import collector_script, ssh_argv, validate_response
from export import build_from_sources, summarize_macro
from lef_profile import parse_lef
from archive import verify_figures


def example(macro):
    return ('''VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS DATABASE MICRONS 2000 ; END UNITS
MACRO ''' + macro + '''
CLASS BLOCK ;
FOREIGN ''' + macro + ''' 0 0 ;
SIZE 10 BY 10 ;
PIN A[0]
DIRECTION INPUT ; USE SIGNAL ;
PORT LAYER metal6 ; RECT 0 0 0.14 0.14 ; END
PORT LAYER metal5 ; RECT 9.86 9.86 10 10 ; END
END A[0]
PIN VDD
DIRECTION INOUT ; USE POWER ;
PORT LAYER metal7 ; RECT 0 0 1 1 ; RECT 2 2 3 3 ; END
END VDD
OBS LAYER metal1 ; RECT 0 0 10 10 ; END
END ''' + macro + '''
END LIBRARY
''').encode()


def fixture():
    cfg = json.loads(CONFIG.read_bytes())
    sources, observations = {}, []
    for item in cfg["files"]:
        data = example(item["macro_name"])
        item["previous_observed_bytes"] = len(data)
        sources[item["id"] + ".lef"] = data
        stamp = [1, 2, len(data), 3]
        observations.append({"id": item["id"], "requested_path": cfg["allowed_root"] + "/" + item["relative_path"],
                             "resolved_path": cfg["allowed_root"] + "/" + item["relative_path"],
                             "bytes": len(data), "sha256": sha(data), "stat_before": stamp,
                             "stat_after": stamp.copy(), "base64": base64.b64encode(data).decode()})
    return cfg, sources, {"observations": observations}


def write_snapshot(folder):
    cfg, sources, response = fixture()
    cfg_bytes = json_bytes(cfg)
    for name, data in sources.items():
        (folder / name).write_bytes(data)
    (folder / "inputs.json").write_bytes(cfg_bytes)
    config_path = (HERE / "inputs.json").relative_to(ROOT).as_posix()
    capture = {"files": file_index(folder), "config_sha256": sha(cfg_bytes), "input_version": cfg["input_version"],
               "remote_user": "yuzelu", "ssh_host": cfg["ssh_host"],
               "upstream": cfg["upstream"], "observations": [{k: v for k, v in r.items() if k != "base64"} for r in response["observations"]],
               "provenance": {"source_dirty": False, "source_commit": "unit-test-only-not-formal-evidence",
                              "source_sha256": {config_path: sha(cfg_bytes)}}}
    (folder / "capture.json").write_bytes(json_bytes(capture))
    return cfg, capture


class PipelineTests(unittest.TestCase):
    def test_outside_geometry_does_not_touch_infinite_extension_of_macro_side(self):
        data = example("test").replace(b"RECT 0 0 0.14 0.14", b"RECT -1 100 1 101").replace(
            b"RECT 9.86 9.86 10 10", b"RECT 100 -1 101 1")
        summary = summarize_macro(parse_lef(data), {"qualified_hard_macro": False})
        self.assertEqual(summary["signal_pin_boundary_touches"], {"no_boundary_touch": 1})

    def test_readback_rejects_unstable_capture_metadata(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            _, capture = write_snapshot(folder)
            capture["observations"][0]["stat_after"][3] += 1
            (folder / "capture.json").write_bytes(json_bytes(capture))
            with self.assertRaises(AssertionError):
                load_snapshot(folder, check_code=False)

    @patch("archive.verify_provenance")
    def test_archive_rejects_figures_from_another_run_or_reserved_names(self, _git_provenance):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name) / "figures"
            run = Path(name) / "run"
            folder.mkdir()
            run.mkdir()
            (run / "manifest.json").write_bytes(b"current run")
            for filename in ("signal-pin-centers.png", "signal-pin-centers.svg", "table.md"):
                (folder / filename).write_bytes(b"test artifact")
            report = {"files": file_index(folder), "input_export_manifest_sha256": sha(b"current run"), "provenance": {},
                      "plotter_source_sha256": sha((HERE / "report.py").read_bytes())}
            (folder / "report-manifest.json").write_bytes(json_bytes(report))
            verify_figures(folder, run)
            report["input_export_manifest_sha256"] = sha(b"previous run")
            (folder / "report-manifest.json").write_bytes(json_bytes(report))
            with self.assertRaises(AssertionError):
                verify_figures(folder, run)
            report["input_export_manifest_sha256"] = sha(b"current run")
            report["files"]["summary.json"] = {"bytes": 0, "sha256": sha(b"")}
            (folder / "report-manifest.json").write_bytes(json_bytes(report))
            with self.assertRaises(AssertionError):
                verify_figures(folder, run)

    def test_capture_scope_rejects_extra_or_changed_source_paths(self):
        cfg = json.loads(CONFIG.read_bytes())
        for change in ("extra", "outside", "detailed"):
            changed = copy.deepcopy(cfg)
            if change == "extra":
                changed["files"].append(copy.deepcopy(changed["files"][0]))
            elif change == "outside":
                changed["files"][0]["relative_path"] = "../../somebody/file.lef"
            else:
                changed["files"][0]["relative_path"] = changed["files"][0]["relative_path"].replace(".lef", ".detailed.lef")
            with self.assertRaises(ValueError):
                check_config(changed)

    def test_ssh_uses_explicit_identity_and_strict_noninteractive_host_verification(self):
        argv = ssh_argv("ssh", "member-key", "existing-hosts", "yuzelu@10.129.166.172")
        for option in ("BatchMode=yes", "IdentitiesOnly=yes", "StrictHostKeyChecking=yes", "UpdateHostKeys=no"):
            self.assertIn(option, argv)
        self.assertEqual(argv[-1], "python3 -B -")
        self.assertNotIn("StrictHostKeyChecking=no", argv)
        script = collector_script(json.loads(CONFIG.read_bytes()))
        self.assertIn("resolved.open('rb')", script)
        self.assertNotIn(".write_", script)

    def test_transferred_bytes_and_source_stat_are_checked(self):
        cfg, sources, response = fixture()
        actual, metadata = validate_response(cfg, response)
        self.assertEqual(actual, sources)
        self.assertTrue(all("base64" not in item for item in metadata))
        for key, value in (("sha256", "0" * 64), ("bytes", 1), ("stat_after", [1, 2, 1, 3]),
                           ("requested_path", cfg["allowed_root"] + "/unexpected.lef"),
                           ("resolved_path", "/public/home/other/private.lef")):
            changed = copy.deepcopy(response)
            changed["observations"][0][key] = value
            with self.assertRaises(AssertionError):
                validate_response(cfg, changed)

    def test_remote_response_must_be_exactly_three_unique_files(self):
        cfg, _, response = fixture()
        response["observations"][1] = copy.deepcopy(response["observations"][0])
        with self.assertRaises(AssertionError):
            validate_response(cfg, response)

    def test_upstream_hash_when_present_cannot_be_ignored(self):
        cfg, _, response = fixture()
        cfg["files"][0]["upstream_expected_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            validate_response(cfg, response)

    def test_source_snapshot_hash_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            write_snapshot(folder)
            load_snapshot(folder, check_code=False)
            (folder / "ACT20.lef").write_bytes(b"tampered")
            with self.assertRaises(AssertionError):
                load_snapshot(folder, check_code=False)

    def test_unindexed_snapshot_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            write_snapshot(folder)
            (folder / "unrequested.lef").write_bytes(b"extra")
            with self.assertRaises(AssertionError):
                load_snapshot(folder, check_code=False)

    def test_csv_and_inventory_retain_pg_multi_rect_and_separate_ports(self):
        cfg, sources, response = fixture()
        _, observations = validate_response(cfg, response)
        capture = {"files": {name: {"sha256": sha(data)} for name, data in sources.items()}}
        outputs = build_from_sources(cfg, capture, "unit-test-capture-hash", sources)
        parsed = json.loads(outputs["inventory.json"])
        summary = json.loads(outputs["summary.json"])
        rows = list(csv.DictReader(io.StringIO(outputs["pin-rectangles.csv"].decode())))
        obs = list(csv.DictReader(io.StringIO(outputs["obs-rectangles.csv"].decode())))
        self.assertEqual(summary["total_pins"], 6)
        self.assertEqual(summary["signal_pins"], 3)
        self.assertEqual(len(rows), 12)
        self.assertEqual(len(obs), 3)
        signal = [r for r in rows if r["candidate"] == "ACT20" and r["pin_raw_name"] == "A[0]"]
        self.assertEqual({r["port_index"] for r in signal}, {"0", "1"})
        self.assertEqual({r["layer"] for r in signal}, {"metal5", "metal6"})
        self.assertEqual(signal[0]["xhi_dbu"], "280")
        macro = parsed["macros"]["ACT20"]["lef"]["macro"]
        self.assertIsNone(macro["origin_um"])
        self.assertIsNone(macro["symmetry"])
        self.assertEqual(len(macro["pins"][1]["ports"][0]["rects"]), 2)
        self.assertEqual(outputs, build_from_sources(cfg, capture, "unit-test-capture-hash", sources))


if __name__ == "__main__":
    unittest.main()
