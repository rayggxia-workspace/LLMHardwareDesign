"""Read-only, source-bound main physical baseline. No EDA or network calls."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
MAIN = "c4d7b960599b9d292f27eb4429d5f226a7156c95"
EVIDENCE = ROOT / "work/YUZE-LU/250/physical/evidence"
BASELINE = Path(__file__).with_name("baseline.json")
EXCLUDED = {"CORE_SPACER", "CORE_WELLTAP", "CORE_ANTENNACELL"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main_blob(path, inputs):
    data = subprocess.run(["git", "show", f"{MAIN}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    inputs[path] = {"git_commit": MAIN, "sha256": sha(data), "bytes": len(data)}
    return data.decode("utf-8-sig")


def physical_box(text):
    rows = {parts[0]: parts[1:] for line in text.splitlines()
            if (parts := line.split("\t"))}
    dbu = int(rows["dbu"][0])
    boxes = {}
    for name in ("die", "core"):
        x0, y0, x1, y1 = map(int, rows[name])
        boxes[name] = {"box_um": [value / dbu for value in (x0, y0, x1, y1)],
                       "area_um2": (x1 - x0) * (y1 - y0) / dbu**2}
    return boxes


def pins(text, expected):
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == expected and len({r["pin"] for r in rows}) == expected
    assert {r["layer"] for r in rows} == {"metal10"}
    return {"signal_bits": expected, "native_layer": "metal10",
            "geometry_source": "final DEF/ODB readback; never an extra wrapper pin",
            "complete_finite_escape_qualified": True,
            "product_route_rc_qualified": False}


def inventory(evidence=EVIDENCE):
    index = json.loads((evidence / "index.json").read_text(encoding="utf-8"))
    assert index["source_commit"] == MAIN
    raw = {}
    for name, record in index["files"].items():
        data = (evidence / name).read_bytes()
        assert sha(data) == record["sha256"], f"Evidence changed: {name}"
        assert len(data) == record["bytes"]
        raw[name] = data.decode("utf-8")
    data = {n: json.loads(t) for n, t in raw.items() if n.endswith(".json")}
    inputs, macros = {}, {}
    prefix = "work/YUZE-LU/143/release-six/M/"
    bundle = json.loads(main_blob(prefix + "bundle.json", inputs))
    # Unlike a fresh receipt, these hashes were already committed in main.
    for local, member in [("M-delivery.json", "native/delivery.json"),
                          ("M-physical.json", "evidence/physical/five-macro-physical.json")]:
        assert sha(raw[local].encode()) == bundle["members"][member]["sha256"]
    m = data["M-physical.json"]
    boxes = physical_box(main_blob(prefix + "evidence/physical/physical-summary.tsv", inputs))
    active = sum(r["area_um2"] for r in m["masters"]
                 if r["signal"] and r["type"] not in EXCLUDED)
    assert not any(r["type"].startswith("BLOCK") for r in m["masters"])
    t = m["timing"]["timed_endpoints"]
    m_pin_rows = main_blob(prefix + "evidence/physical/physical-pins.tsv", inputs).splitlines()
    assert len(m_pin_rows) == 867 and len({r.split("\t")[0] for r in m_pin_rows}) == 867
    assert {r.split("\t")[1] for r in m_pin_rows} == {"metal10"}
    macros["M"] = dict(outline_um=m["die_um"], outline_area_um2=boxes["die"]["area_um2"],
        core_area_um2=boxes["core"]["area_um2"], core_box_um=boxes["core"]["box_um"],
        functional_stdcell_area_um2=active, hardmacro_outline_area_um2=0,
        occupied_outline_ratio=active/boxes["die"]["area_um2"],
        occupied_core_ratio=active/boxes["core"]["area_um2"],
        delivery_active_including_antenna_um2=m["active_area_um2"],
        antenna_excluded_um2=m["active_area_um2"]-active,
        pins=dict(signal_bits=867, native_layer="metal10", complete_finite_escape_qualified=True,
                  product_route_rc_qualified=False),
        setup_ns=t["minimum_setup_ns"], hold_ns=t["minimum_hold_ns"],
        final_odb_sha256=data["M-delivery.json"]["final_files"]["6_final.odb"]["sha256"],
        evidence=["M-delivery.json", "M-physical.json"])
    for name, count in [("G", 108), ("E", 273)]:
        delivery, occ = data[f"{name}-delivery.json"], data[f"{name}-occupancy.json"]
        assert delivery["leaf_accepted"]
        # The release binds occupancy separately; delivery active also includes antenna cells.
        assert delivery["files"]["occupancy.json"]["sha256"] == sha(raw[f"{name}-occupancy.json"].encode())
        area = occ["active_area_um2"]
        pin_file = f"docs/experiments/assets/compact-ge/{name}-pins.csv"
        macros[name] = dict(outline_um=delivery["die_um"],
            outline_area_um2=delivery["die_um"][0]*delivery["die_um"][1],
            core_area_um2=area/occ["active_core_ratio"], functional_stdcell_area_um2=area,
            hardmacro_outline_area_um2=0, occupied_outline_ratio=occ["active_outline_ratio"],
            occupied_core_ratio=occ["active_core_ratio"],
            delivery_active_including_antenna_um2=delivery["final_active_um2"],
            antenna_excluded_um2=delivery["final_active_um2"]-area,
            largest_empty_10um_grid_region_um2=occ["largest_connected_empty_region_um2"],
            pins=pins(main_blob(pin_file, inputs), count),
            setup_ns=delivery["timing"]["timed_endpoints"]["minimum_setup_ns"],
            hold_ns=delivery["timing"]["timed_endpoints"]["minimum_hold_ns"],
            final_odb_sha256=delivery["files"]["6_final.odb"]["sha256"],
            evidence=[f"{name}-delivery.json", f"{name}-occupancy.json"])
    for name, filename, count in [("S_base", "S-base", 273), ("S_P", "S-P", 965)]:
        audit, receipt, occ = [data[f"{name}-{suffix}.json"] for suffix in ("audit", "receipt", "occupancy")]
        assert audit["passed"] and all(audit["checks"].values())
        assert audit["final_sha256"] == receipt["final_sha256"]
        assert receipt["native_gds_drc_items"] == 0
        boxes = physical_box(raw[f"{name}-physical-summary.tsv"])
        active, bank = occ["area_um2"]["active"], occ["area_um2"]["bank"]
        assert occ["counts"]["bank"] == 4
        macros[name] = dict(outline_um=receipt["die_um"],
            outline_area_um2=boxes["die"]["area_um2"], core_area_um2=boxes["core"]["area_um2"],
            core_box_um=boxes["core"]["box_um"], functional_stdcell_area_um2=active,
            hardmacro_outline_area_um2=bank, hardmacro_count=4, usable_storage_bytes=16384,
            physical_storage_bytes=16384, occupied_outline_ratio=(active+bank)/boxes["die"]["area_um2"],
            occupied_core_ratio=(active+bank)/boxes["core"]["area_um2"],
            hardmacro_outline_ratio=bank/boxes["die"]["area_um2"],
            sparse_bins_16x10=occ["bins_under_10pct"],
            pins=pins(main_blob(f"docs/experiments/assets/compact-local-s/{filename}-pins.csv", inputs), count),
            setup_ns=audit["setup_ns"], hold_ns=audit["hold_ns"],
            final_odb_sha256=audit["final_sha256"]["6_final.odb"],
            evidence=[f"{name}-audit.json", f"{name}-receipt.json", f"{name}-occupancy.json",
                      f"{name}-physical-summary.tsv"])
    return dict(schema="issue250-compact-physical-baseline/1", main_commit=MAIN,
        area_policy="Functional standard cells plus hard-macro outlines; exclude filler/tap/endcap/antenna. Never add macro internal cell area again.",
        acceptance_scope="Existing independent TT 1.1V 25C Nangate45 M1-M10 leaves at 300MHz. Finite M11/M12 escape is not product routing or electrical qualification.",
        new_hardware_qualified=False, macros=macros, main_inputs=inputs,
        copied_evidence_index_sha256=sha((evidence/"index.json").read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = inventory()
    if args.check:
        assert json.loads(BASELINE.read_text(encoding="utf-8")) == result, "Baseline differs; inspect inputs before updating"
        print("PASS: 14 copied reports, 5 main leaf baselines, exact pins and source bindings")
    if args.output:
        args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    if not args.check and not args.output:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
