"""Measure candidate area and the inherited full-port strip planning constraint.

This is a declared geometry/area diagnostic, NOT placement, routing or RC.
It deliberately exposes the cost of forcing every wider port to a macro edge;
it does not silently enlarge and qualify the candidate macro.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "project/experiments/block_v1"))
from revision300_ports import generate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapping", type=Path, required=True)
    p.add_argument("--liberty", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = json.loads(args.mapping.read_text())
    assert source["passed"] and len(source["results"]) == 2
    text = args.liberty.read_text()
    starts = list(re.finditer(r"\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{", text))
    areas = {}
    for i, match in enumerate(starts):
        chunk = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
        areas[match[1]] = float(re.search(r"\barea\s*:\s*([\d.eE+-]+)\s*;", chunk)[1])
    technology_path = ROOT / "project/experiments/block_v1/technology-2um-v1.json"
    technology = json.loads(technology_path.read_text())
    results = []
    for receipt in source["results"]:
        assert receipt["passed"] and receipt["liberty_sha256"] == sha(args.liberty)
        for name, digest in receipt["source_sha256"].items():
            assert sha(ROOT / name) == digest
        active = sum(areas[name] * count for name, count in receipt["cell_counts"].items())
        side = max(400, math.ceil((math.sqrt(active / .4) + 40) / 10) * 10)
        area_side = side
        while True:
            try:
                plan, fixture, proof = generate(receipt["ports"], side, technology)
                break
            except AssertionError as exc:
                if not exc.args or not isinstance(exc.args[0], tuple) or exc.args[0][0] != "Insufficient full-port tracks; enlarge native footprint":
                    raise
                side += 10
                assert side < 5000
        name = receipt["top"]
        (args.out / (name + "-strip-plan.json")).write_text(json.dumps(plan, indent=2) + "\n")
        results.append(dict(top=name, mapped_cells=receipt["cell_count"], mapped_cell_area_um2=active,
                            area_rule_side_um=area_side, inherited_strip_minimum_side_um=side,
                            area_rule="ceil10(sqrt(mapped_cell_area/.40)+40), minimum400",
                            strip_footprint_ratio=(side / area_side) ** 2,
                            signal_pins=receipt["signal_pin_bits"],
                            inputs=sum(p["bits"] for p in receipt["ports"].values() if p["direction"] == "input"),
                            outputs=sum(p["bits"] for p in receipt["ports"].values() if p["direction"] == "output"),
                            track_demand=plan["track_demand"], track_capacity=plan["track_capacity"],
                            declared_geometry_check=proof, physical_qualified=False))
    result = dict(passed=True, results=results, inputs_sha256={str(args.mapping): sha(args.mapping),
                  str(args.liberty): sha(args.liberty), str(technology_path): sha(technology_path),
                  "plan.py": sha(Path(__file__))},
                  scope="Area and inherited simultaneous edge-escape diagnostic only. No placed/routed macro, independent GDS check, calibrated RC, timing or drive qualification. Strip minima are NOT frozen new macro dimensions.")
    (args.out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
