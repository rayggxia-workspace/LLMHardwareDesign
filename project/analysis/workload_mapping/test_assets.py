"""Meaningful asset/binding tests, including authorized local continuation.

Optional WORKLOAD_ASSET_ROOT enables full pinned ACT/MXU/GEMM source checks.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assets

def synthetic_catalog():
    data = b"""VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
 DATABASE MICRONS 2000 ;
END UNITS
MACRO synthetic_pair
 CLASS BLOCK ;
 SIZE 2 BY 2 ;
 PIN tx[0]
  DIRECTION OUTPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal5 ;
   RECT 0 0 0.1 0.1 ;
  END
 END tx[0]
 PIN tx[1]
  DIRECTION OUTPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal6 ;
   RECT 0.2 0 0.3 0.1 ;
  END
 END tx[1]
 PIN rx[0]
  DIRECTION INPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal5 ;
   RECT 0 1 0.1 1.1 ;
  END
 END rx[0]
 PIN rx[1]
  DIRECTION INPUT ;
  USE SIGNAL ;
  PORT
   LAYER metal6 ;
   RECT 0.2 1 0.3 1.1 ;
  END
 END rx[1]
 OBS
  LAYER metal1 ;
  RECT 0.5 0.5 1.5 1.5 ;
 END
END synthetic_pair
END LIBRARY
"""
    geom = assets._parser()(data, "synthetic-inline.lef")
    identity = {"project": "synthetic", "case_id": "ordered_pair", "source_commit": "0" * 40,
                "run_version": "synthetic-v1", "master": "synthetic_pair",
                "file_sha256": hashlib.sha256(data).hexdigest()}
    ports = [{"name": name, "bits": [0, 1], "direction": direction, "protocol": "test-ready-valid/1",
              "format": "u2", "evidence": "assumed", "source": "synthetic/test_assets.py"} for name, direction in (("tx", "OUTPUT"), ("rx", "INPUT"))]
    asset = {"asset_id": "synthetic-pair", "identity": identity, "synthetic": True, "evidence": "assumed",
             "source": {"path": "synthetic-inline.lef", "url": None}, "coordinate_system": "macro_local",
             "position": None, "orientation": None, "ports": ports, "geometry": geom,
             "qualified_hard_macro": False, "protocol": None, "clock_reset_policy": None,
             "frozen_base": None, "fixed_m8_access": None, "verified_scope": ["synthetic_test_fixture"]}
    return {"schema": assets.CATALOG_SCHEMA, "assets": [asset], "availability": [{"asset_id": "synthetic-pair", "status": "pass"}],
            "scope": "synthetic fixture only", "synthetic": True, "status": "pass"}

def synthetic_request(catalog):
    identity = catalog["assets"][0]["identity"]
    return {"schema": assets.BINDING_SCHEMA,
            "instances": [{"instance_id": name, "asset_id": "synthetic-pair", "identity": copy.deepcopy(identity)}
                          for name in ("a", "b")],
            "bindings": [
                {"binding_id": "src", "instance_id": "a", "resource_endpoint": "declared-a.out",
                 "port": "tx", "bits": [0, 1], "direction": "OUTPUT", "protocol": "test-ready-valid/1", "format": "u2"},
                {"binding_id": "dst", "instance_id": "b", "resource_endpoint": "declared-b.in",
                 "port": "rx", "bits": [0, 1], "direction": "INPUT", "protocol": "test-ready-valid/1", "format": "u2"}],
            "connections": [{"connection_id": "a-b", "source": "src", "target": "dst", "bit_pairs": [[0, 0], [1, 1]]}]}

class AssetTests(unittest.TestCase):
    def setUp(self):
        self.catalog = synthetic_catalog()
        self.request = synthetic_request(self.catalog)

    def rejected(self):
        report = assets.bind(self.catalog, self.request)
        self.assertEqual(report["status"], "fail", report)
        self.assertEqual(report["reference_port_check"]["status"], "fail")

    def test_explicit_contract_passes(self):
        self.assertEqual(assets.validate_catalog(self.catalog)["status"], "pass")
        report = assets.bind(self.catalog, self.request)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["physical_binding"]["status"], "not_executed")

    def test_geometry_hierarchy_retained(self):
        geom = self.catalog["assets"][0]["geometry"]
        self.assertEqual(geom["header"]["dbu_per_micron"], 2000)
        self.assertEqual(geom["macro"]["pins"][0]["ports"][0]["rects"][0]["rect_dbu"], [0, 0, 200, 200])
        self.assertEqual(geom["macro"]["obstructions"][0]["rects"][0]["layer"], "metal1")
        self.assertIsNone(geom["macro"]["origin_um"])

    def test_nonexistent_pin(self):
        self.request["bindings"][0]["port"] = "missing"
        self.rejected()

    def test_missing_bit(self):
        self.request["bindings"][0]["bits"] = [0]
        self.rejected()

    def test_duplicate_bit(self):
        self.request["bindings"][0]["bits"] = [0, 0]
        self.rejected()

    def test_wrong_logical_order(self):
        self.request["bindings"][0]["bits"] = [1, 0]
        self.rejected()

    def test_wrong_direction(self):
        self.request["bindings"][0]["direction"] = "INPUT"
        self.rejected()

    def test_protocol_same_width_conflict(self):
        self.request["bindings"][1]["protocol"] = "unrelated-serial/1"
        self.rejected()

    def test_format_conflict(self):
        self.request["bindings"][1]["format"] = "packed-signed-2"
        self.rejected()

    def test_ordered_connection_pairs(self):
        self.request["connections"][0]["bit_pairs"] = [[1, 1], [0, 0]]
        self.rejected()

    def test_duplicate_sink_driver(self):
        extra = copy.deepcopy(self.request["connections"][0])
        extra["connection_id"] = "duplicate-driver"
        self.request["connections"].append(extra)
        self.rejected()

    def test_missing_binding_reference(self):
        self.request["connections"][0]["target"] = "absent"
        self.rejected()

    def test_old_new_run_mix_rejected(self):
        self.request["instances"][0]["identity"]["run_version"] = "new-matched-issue55"
        self.rejected()

    def test_same_master_different_file_rejected(self):
        self.request["instances"][0]["identity"]["file_sha256"] = "a" * 64
        self.rejected()

    def test_unknown_protocol_blocked(self):
        self.catalog["assets"][0]["ports"] = []
        report = assets.bind(self.catalog, self.request)
        self.assertEqual(report["reference_port_check"]["status"], "pass")
        self.assertEqual(report["protocol_check"]["status"], "blocked")
        self.assertEqual(report["status"], "blocked")

    def test_unknown_format_blocked(self):
        self.request["bindings"][0]["format"] = None
        report = assets.bind(self.catalog, self.request)
        self.assertEqual(report["protocol_check"]["status"], "blocked")

    def test_physical_missing_m8_blocked(self):
        # Even optimistic caller-injected flags do not replace qualified evidence.
        self.catalog["assets"][0]["fixed_m8_access"] = {"claimed": True}
        self.catalog["assets"][0]["frozen_base"] = {"claimed": True}
        report = assets.bind(self.catalog, self.request, physical=True)
        self.assertEqual(report["reference_port_check"]["status"], "pass")
        self.assertEqual(report["physical_binding"]["status"], "blocked")
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any("M8" in x["reason"] for x in report["physical_binding"]["checks"]))

    def test_mixed_units_rejected(self):
        self.catalog["assets"][0]["geometry"]["macro"]["pins"][0]["ports"][0]["rects"][0]["rect_dbu"][2] = 201
        self.assertEqual(assets.validate_catalog(self.catalog)["status"], "fail")

    def test_unknown_fields_rejected(self):
        self.request["bindings"][0]["bandwdith"] = 2
        self.rejected()

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(assets.AssetError):
                assets.read_json(path)

    def test_missing_sources_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = assets.import_assets(tmp)
            self.assertEqual(catalog["status"], "blocked")
            self.assertEqual(len(catalog["availability"]), 3)
            self.assertEqual({r["case_id"] for r in catalog["availability"]}, {"ACT20", "MXU20", "GEMM20"})
            self.assertTrue(all(r["status"] == "blocked" for r in catalog["availability"]))

    def test_missing_source_catalog_does_not_validate_as_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = assets.import_assets(tmp)
            self.assertEqual(assets.validate_catalog(catalog, dependency_root=tmp)["status"], "blocked")

    def test_empty_catalog_cannot_claim_validation(self):
        self.catalog["assets"] = []
        self.catalog["availability"] = []
        self.assertEqual(assets.validate_catalog(self.catalog)["status"], "fail")

    def test_forged_successful_availability_rejected(self):
        self.catalog["assets"] = []
        self.assertEqual(assets.validate_catalog(self.catalog)["status"], "fail")

    def test_sha_tamper_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inputs" / "ACT20.lef"
            path.parent.mkdir()
            path.write_bytes(b"bad source")
            catalog = assets.import_assets(tmp)
            self.assertEqual(catalog["availability"][0]["status"], "fail")
            self.assertEqual(catalog["status"], "fail")

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = Path(tmp) / "root", Path(tmp) / "outside"
            root.mkdir(); outside.mkdir()
            (root / "inputs").symlink_to(outside, target_is_directory=True)
            catalog = assets.import_assets(root)
            self.assertTrue(all(r["status"] == "fail" for r in catalog["availability"]))

    @unittest.skipUnless(os.environ.get("WORKLOAD_ASSET_ROOT"), "full reference snapshots not supplied")
    def test_real_opentpu_and_llaccel_import(self):
        catalog = assets.import_assets(os.environ["WORKLOAD_ASSET_ROOT"])
        self.assertEqual(catalog["status"], "pass")
        self.assertEqual(assets.validate_catalog(catalog, dependency_root=os.environ["WORKLOAD_ASSET_ROOT"])["status"], "pass")
        records = {a["identity"]["case_id"]: a for a in catalog["assets"]}
        self.assertEqual({k: len(v["geometry"]["macro"]["pins"]) for k, v in records.items()},
                         {"ACT20": 862, "MXU20": 2174, "GEMM20": 3755})
        # Independent known observed ACT coordinate from the original raw LEF.
        clk = next(p for p in records["ACT20"]["geometry"]["macro"]["pins"] if p["name"] == "clk")
        self.assertEqual(clk["ports"][0]["rects"][0]["rect_um"], ["62.185", "0", "62.325", "0.14"])
        self.assertEqual(clk["direction"], "INPUT")
        self.assertEqual(clk["use"], "SIGNAL")
        self.assertTrue(all(a["protocol"] is None and not a["qualified_hard_macro"] for a in records.values()))
        self.assertTrue(all(a["coordinate_system"] == "macro_local" for a in records.values()))

    @unittest.skipUnless(os.environ.get("WORKLOAD_ASSET_ROOT"), "full reference snapshots not supplied")
    def test_real_catalog_without_originals_blocked(self):
        catalog = assets.import_assets(os.environ["WORKLOAD_ASSET_ROOT"])
        self.assertEqual(assets.validate_catalog(catalog)["status"], "blocked")

    @unittest.skipUnless(os.environ.get("WORKLOAD_ASSET_ROOT"), "full reference snapshots not supplied")
    def test_catalog_tamper_cannot_hide_behind_original_hash(self):
        catalog = assets.import_assets(os.environ["WORKLOAD_ASSET_ROOT"])
        rect = catalog["assets"][0]["geometry"]["macro"]["pins"][0]["ports"][0]["rects"][0]
        rect["rect_um"], rect["rect_dbu"] = ["0", "0", "0.1", "0.1"], [0, 0, 200, 200]
        report = assets.validate_catalog(catalog, dependency_root=os.environ["WORKLOAD_ASSET_ROOT"])
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("reparsed" in x.get("reason", "") for x in report["checks"]))

    @unittest.skipUnless(os.environ.get("WORKLOAD_ASSET_ROOT"), "full reference snapshots not supplied")
    def test_new_hash_cannot_replace_pinned_reference(self):
        catalog = assets.import_assets(os.environ["WORKLOAD_ASSET_ROOT"])
        catalog["assets"][0]["identity"]["file_sha256"] = "a" * 64
        catalog["assets"][0]["geometry"]["source_sha256"] = "a" * 64
        self.assertEqual(assets.validate_catalog(catalog, dependency_root=os.environ["WORKLOAD_ASSET_ROOT"])["status"], "fail")

    def test_real_asset_id_cannot_be_relabelled_synthetic(self):
        self.catalog["assets"][0]["asset_id"] = "reference-wave2-06-ACT20"
        self.assertEqual(assets.validate_catalog(self.catalog)["status"], "fail")

    @unittest.skipUnless(os.environ.get("WORKLOAD_ASSET_ROOT"), "full reference snapshots not supplied")
    def test_claimed_real_protocol_cannot_authenticate_itself(self):
        catalog = assets.import_assets(os.environ["WORKLOAD_ASSET_ROOT"])
        catalog["assets"][0]["ports"] = [{"name": "clk", "bits": [None], "direction": "INPUT",
                                        "protocol": "invented", "format": "u1", "evidence": "observed",
                                        "source": "self-asserted"}]
        self.assertEqual(assets.validate_catalog(catalog, dependency_root=os.environ["WORKLOAD_ASSET_ROOT"])["status"], "fail")

if __name__ == "__main__":
    unittest.main()
