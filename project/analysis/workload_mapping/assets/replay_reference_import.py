"""Offline selected LEF import and independent PR20 bit-source audit.

Run inside a checkout with original fixed snapshots supplied explicitly.
This does not run Liberty timing or the original upstream complete pipelines.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

MODULE = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(MODULE))
import assets

ARCHIVE20_SHA = "2d2047b761323ba22e3c209d83a25a89fc77e901beae166103908df72de986d7"
MANIFEST20_SHA = "dd4c0c5f8ec678abcc8dc849cd22966f2e2f0e66ed65b200ea84c70d32e9e154"
BITS_SHA = "2c792674a528217e6f277aac92318a2d87fbd9fa6303593ad4775b2ae9844057"

def require(condition, message):
    if not condition:
        raise assets.AssetError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def audit_pr20(root, catalog):
    path = root / "pr20" / "evidence.zip"
    if not path.is_file():
        return {"status": "blocked", "missing": ["pr20/evidence.zip"],
                "scope": "selected old ACT/MXU bit-source audit"}
    raw = path.read_bytes()
    require(digest(raw) == ARCHIVE20_SHA, "PR20 archive SHA mismatch")
    imported = {a["identity"]["case_id"]: a for a in catalog["assets"]}
    checked = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest_raw = archive.read("manifest.json")
        require(digest(manifest_raw) == MANIFEST20_SHA, "PR20 manifest SHA mismatch")
        manifest = json.loads(manifest_raw, object_pairs_hook=assets._unique)
        def read_member(name):
            data = archive.read(name)
            record = manifest["files"][name]
            require(len(data) == record["bytes"] and digest(data) == record["sha256"],
                    "PR20 member SHA/size mismatch: " + name)
            checked.append({"path": name, "bytes": len(data), "sha256": digest(data)})
            return data
        bit_raw = read_member("bits.csv")
        require(digest(bit_raw) == BITS_SHA, "PR20 bit CSV SHA mismatch")
        rows = list(csv.DictReader(io.StringIO(bit_raw.decode("utf-8"))))
        require(len(rows) == 3032, "PR20 bit count differs from independent known value")
        require(len({(r["candidate"], r["bit_name"]) for r in rows}) == len(rows),
                "duplicate PR20 bit rows")
        require({r["candidate"] for r in rows} == {"ACT20", "MXU20"}, "unexpected candidate")
        cases = []
        for case, master, count in (("ACT20", "llhd_opentpu_act", 860), ("MXU20", "llhd_opentpu_mxu", 2172)):
            asset = imported[case]
            old_lef = read_member("inputs/" + case + ".lef")
            require(digest(old_lef) == asset["identity"]["file_sha256"], "old/new LEF version mixing")
            elab_raw = read_member("inputs/" + case + "/elab.json")
            elab = json.loads(elab_raw, object_pairs_hook=assets._unique)
            ports = elab["modules"][master]["ports"]
            pins = {p["name"]: p for p in asset["geometry"]["macro"]["pins"] if p["use"] == "SIGNAL"}
            source_bits, expected_positions = {}, {}
            for port_name, port in ports.items():
                ids = port["bits"]
                width, offset, upto = len(ids), port.get("offset", 0), port.get("upto", 0)
                require(type(offset) is int and type(upto) is int and upto in (0, 1), "unsupported Yosys index")
                vector = width > 1 or port_name not in pins
                expected_positions[port_name] = list(range(width))
                for pos, bit in enumerate(ids):
                    index = offset + (width - 1 - pos if upto else pos) if vector else None
                    name = port_name + ("[" + str(index) + "]" if vector else "")
                    require(name not in source_bits, "duplicate expanded source bit")
                    source_bits[name] = {"port": port_name, "position": pos, "index": index,
                                         "direction": port["direction"], "yosys_bit": str(bit)}
            require(set(source_bits) == set(pins), "Yosys/LEF signal pin sets differ")
            selected = [r for r in rows if r["candidate"] == case]
            require(len(selected) == count == len(pins), "source count mismatch")
            observed_positions = {name: [] for name in ports}
            for row in selected:
                bit = source_bits[row["bit_name"]]
                pin = pins[row["bit_name"]]
                require(row["port"] == bit["port"] and int(row["lsb_position"]) == bit["position"],
                        "CSV source port/bit-position mismatch")
                require(row["hdl_index"] == ("" if bit["index"] is None else str(bit["index"])),
                        "CSV HDL index mismatch")
                require(row["direction"] == bit["direction"] == pin["direction"].lower(),
                        "CSV/Yosys/LEF direction mismatch")
                require(row["yosys_bit"] == bit["yosys_bit"], "CSV Yosys ID/constant mismatch")
                require(row["lef_use"] == pin["use"] and int(row["lef_line"]) == pin["line"],
                        "CSV LEF declaration mismatch")
                require(int(row["rect_count"]) == sum(len(p["rects"]) for p in pin["ports"]),
                        "CSV geometry rectangle count mismatch")
                require(row["legal_access_verified"] == "False", "unexpected physical qualification")
                observed_positions[bit["port"]].append(bit["position"])
            require(observed_positions == expected_positions, "CSV port order/coverage differs from source order")
            cases.append({"case_id": case, "status": "pass", "signal_bits": count,
                          "logical_ports": len(ports), "protocol": "unknown",
                          "scope": "Yosys ordered bit indices/IDs, exported CSV and same-version LEF names/directions"})
    return {"status": "pass", "source_commit": "cce235975b7be6d77247c9c9c7b09ea15608e2cf",
            "archive_sha256": ARCHIVE20_SHA, "bits": 3032, "cases": cases, "checked_members": checked,
            "not_verified": ["Liberty syntax/timing", "full RTL equivalence", "protocol semantics",
                             "physical access", "complete original PR20 pipeline replay"]}

def verify(reference_root):
    root = Path(reference_root).resolve(strict=True)
    catalog = assets.import_assets(root)
    require(catalog["status"] == "pass", "LEF import did not pass")
    validation = assets.validate_catalog(catalog, dependency_root=root)
    require(validation["status"] == "pass", "fixed source catalog verification did not pass")
    expected = assets.read_json(MODULE / "assets" / "reference_expected.json")
    summaries = []
    for asset in catalog["assets"]:
        case = asset["identity"]["case_id"]
        exp = next(e for e in expected["cases"] if e["case_id"] == case)
        geom, header = asset["geometry"]["macro"], asset["geometry"]["header"]
        signals = [p for p in geom["pins"] if p["use"] == "SIGNAL"]
        require(len(geom["pins"]) == exp["total_pins"] and len(signals) == exp["signal_pins"], "known pin count mismatch")
        require(geom["name"] == exp["master"] and geom["size_um"] == exp["size_um"], "known master/size mismatch")
        require(header["dbu_per_micron"] == exp["dbu_per_micron"], "unit mismatch")
        layers = {}
        for pin in signals:
            for layer in {r["layer"] for p in pin["ports"] for r in p["rects"]}:
                layers[layer] = layers.get(layer, 0) + 1
        require(layers == exp["signal_pins_by_layer"], "known layer count mismatch")
        summaries.append({"case_id": case, "project": asset["identity"]["project"], "status": "pass",
                          "identity": asset["identity"], "evidence": "observed", "synthetic": False,
                          "total_pins": len(geom["pins"]), "signal_pins": len(signals),
                          "pin_rectangles": sum(len(p["rects"]) for pin in geom["pins"] for p in pin["ports"]),
                          "obstruction_rectangles": sum(len(o["rects"]) for o in geom["obstructions"]),
                          "size_um": geom["size_um"], "dbu_per_micron": header["dbu_per_micron"],
                          "coordinate_system": "macro_local", "origin_explicit": geom["origin_explicit"],
                          "symmetry": geom["symmetry"], "qualified_hard_macro": False})
    request = assets.read_json(MODULE / "assets" / "reference_binding.example.json")
    binding = assets.bind(catalog, request, dependency_root=root, physical=True)
    require(binding["reference_port_check"]["status"] == "pass", "actual ACT pin reference failed")
    require(binding["protocol_check"]["status"] == "blocked", "unknown protocol must remain blocked")
    require(binding["physical_binding"]["status"] == "blocked", "physical evidence must remain blocked")
    return {"schema": "workload-reference-import-summary/1", "reference_import": "pass",
            "scope": "Three selected old macro LEFs; not two full designs or final Blocks",
            "source_commit": "19c4b829211678d1a6fefa61bc0a23e68e4f13e1",
            "server_access": False, "cases": summaries, "catalog_validation": validation,
            "reference_binding": binding, "pr20_selected_bit_audit": audit_pr20(root, catalog)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if REPO not in output.parents:
        parser.error("output must be a new directory within this checkout")
    output.mkdir(parents=True, exist_ok=False)
    try:
        summary = verify(args.reference_root)
        data = (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8")
        (output / "summary.json").write_bytes(data)
        receipt = {"python": sys.version, "platform": platform.platform(),
                   "source_sha256": {p.name: digest(p.read_bytes()) for p in
                                    [Path(__file__), MODULE / "assets.py", MODULE / "assets" / "reference_lef_profile.py"]},
                   "summary_sha256": digest(data), "status": "pass",
                   "scope": "reference import and selected bit audit; protocol and physical binding remain blocked"}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"reference_import": summary["reference_import"],
                          "pr20_bits": summary["pr20_selected_bit_audit"]["status"],
                          "physical_binding": summary["reference_binding"]["physical_binding"]["status"],
                          "summary_sha256": digest(data)}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        (output / "failure.json").write_text(json.dumps({"status": "fail", "reason": str(exc)}, indent=2) + "\n",
                                            encoding="utf-8", newline="\n")
        print(str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
