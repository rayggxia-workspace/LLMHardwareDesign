"""Compute a conservative planar wire-length cost from accepted pin rectangles."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def parse_rects(lef, units):
    rects = {}
    pattern = r"^\s+PIN\s+(\S+)\s*$([\s\S]*?)^\s+END\s+\1\s*$"
    for name, body in re.findall(pattern, lef, re.M):
        layer10 = re.findall(r"\bLAYER\s+metal10\s*;([\s\S]*?)(?=\bLAYER\b|$)", body)
        points = []
        for section in layer10:
            for raw in re.findall(r"\bRECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;", section):
                scaled = [Decimal(v) * units for v in raw]
                if any(v != int(v) for v in scaled):
                    raise ValueError("nonintegral LEF coordinate in DEF units")
                points.append(tuple(map(int, scaled)))
        if points:
            rects[name] = points
    return rects


def distance(a, b):
    return max(0, b[0]-a[2], a[0]-b[2]) + max(0, b[1]-a[3], a[1]-b[3])


def analyze(lef_bytes, def_bytes, meta, um_per_cost):
    lef, layout = lef_bytes.decode(), def_bytes.decode()
    units, = re.findall(r"^UNITS DISTANCE MICRONS\s+(\d+)\s*;", layout, re.M)
    units = int(units)
    if hashlib.sha256(lef_bytes).hexdigest() != meta["p16_lef_sha256"]:
        raise ValueError("LEF differs from coupon receipt")
    coords = {name: (int(x), int(y)) for name, x, y in re.findall(
        r"^- (P[01]) \S+ \+ FIXED \( (\d+) (\d+) \) N ;$", layout, re.M)}
    if set(coords) != {"P0", "P1"}:
        raise ValueError("coupon must use both P16 placements in orientation N")
    rects = parse_rects(lef, units)
    nets = re.findall(r"^- (up_data_\d+) \( (P1) (\S+) \) \( (P0) (\S+) \) \+ USE SIGNAL ;$", layout, re.M)
    if {net[0] for net in nets} != {f"up_data_{i}" for i in range(128)} or len(nets) != 128:
        raise ValueError("unexpected FFN payload")
    lengths = {}
    for name, a, ap, b, bp in nets:
        def placed(block, port):
            x, y = coords[block]
            return [(x+l, y+d, x+r, y+u) for l,d,r,u in rects[port]]
        lengths[name] = min(distance(x, y) for x in placed(a, ap) for y in placed(b, bp))
    total = sum(lengths.values())
    return {
        "base_id": meta["base_id"], "bundle_id": meta["bundle_id"],
        "kind": "m10_pin_rectangle_wire_lower_bound", "result": "penalty",
        "incremental_cost": total // (units * um_per_cost),
        "evidence_sha256": hashlib.sha256(lef_bytes + b"\x00" + def_bytes).hexdigest(),
        "def_sha256": hashlib.sha256(def_bytes).hexdigest(),
        "lef_sha256": meta["p16_lef_sha256"],
        "units_per_um": units, "um_per_cost": um_per_cost,
        "total_wire_lower_bound_dbu": total, "wire_lower_bound_dbu": lengths,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("lef", type=Path)
    p.add_argument("coupon_def", type=Path)
    p.add_argument("coupon_json", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--um-per-cost", type=int, default=16)
    args = p.parse_args()
    if args.um_per_cost <= 0:
        p.error("um-per-cost must be positive")
    result = analyze(args.lef.read_bytes(), args.coupon_def.read_bytes(),
                     json.loads(args.coupon_json.read_bytes()), args.um_per_cost)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
