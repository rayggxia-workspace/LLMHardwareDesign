"""Certify a continuous geometric cut bound for the intact PR271-A netlist."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from geometry import NativePins, access_points, contains

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("placement", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
raw = args.input.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == "31ffb0b6e7ec5fc05b39bc93b340f892cb2b99097a01a24f8f4f3e24ba9115e8"
spec = json.loads(raw)
layout = json.loads(args.placement.read_bytes())
assert layout["variant"] == "pr271_A"
with (args.input.parent/"nets.tsv").open() as source:
    family = {r["net_id"]: r["family"] for r in csv.DictReader(source, delimiter="\t")}
assert len(spec["nets"]) == 1834 and set(family) == {r["id"] for r in spec["nets"]}
assert Counter(family.values()) == {"gather.U0.dma3": 650, "packet": 1031, "decode.index.transport": 153}
tech = spec["technology"]
gap = tech["width"] + tech["spacing"]
pins = spec["pins"]
native = NativePins(spec)
locations = {}
used = set()
for net in spec["nets"]:
    group = {net["driver"], *net["sinks"]}
    used.update(group)
    for pin in group:
        choices = [p for p in access_points(pins[pin],tech) if native.exclusive(p,group)]
        location, = choices
        locations[pin] = location

rows = {}
for macro, outline in sorted(layout["boxes_dbu"].items()):
    terminals = sorted(pin for pin in used if pin.split("/",1)[0] == macro)
    if not terminals:
        continue
    xs, ys = zip(*(locations[p] for p in terminals))
    outer = (min(xs)-1,min(ys)-1,max(xs)+1,max(ys)+1)
    outer_candidates = [(outer, "terminal-center cut")]
    if contains(outline, outer):
        outer_candidates.append((outline, "declared block-outline cut"))
    for rect, label in outer_candidates:
        l,b,r,t = rect
        inside = {pin for pin,(x,y) in locations.items() if l<x<r and b<y<t}
        outside = {pin for pin,(x,y) in locations.items() if x<l or x>r or y<b or y>t}
        required = []
        for net in spec["nets"]:
            terminals = {net["driver"],*net["sinks"]}
            if terminals & inside and terminals & outside:
                required.append(net["id"])
        # Count the largest number of centers that can be placed on each side
        # when crossings from different nets on the same layer are gap apart.
        # Allow a center at each corner and arbitrary continuous track origins.
        cap_m11 = (t-b)//gap + 1
        cap_m12 = (r-l)//gap + 1
        capacity = 2*(cap_m11+cap_m12)
        rows[macro+"/"+label] = {
            "bounds_dbu": rect, "declared_outline_dbu": outline,
            "crossing_nets": len(required), "by_family": dict(Counter(family[n] for n in required)),
            "M11_per_vertical_side": cap_m11, "M12_per_horizontal_side": cap_m12,
            "optimistic_max_distinct_crossings": capacity,
            "capacity_deficit": max(0,len(required)-capacity),
            "net_ids": required,
            "cut_crosses_no_terminal_center": len(inside)+len(outside)==len(used),
        }

certificate = {"placement": layout["variant"], "input_sha256": digest,
               "placement_sha256": hashlib.sha256(args.placement.read_bytes()).hexdigest(),
               "net_count": len(family), "u0_dma_count": 650, "required_center_spacing_dbu": gap,
               "scope": "fixed M10 landing centers; upper-only M11 horizontal and M12 vertical routes",
               "cuts": rows}
args.output.write_text(json.dumps(certificate, indent=2)+"\n")
for n,row in rows.items():
    print(n,row["crossing_nets"],row["optimistic_max_distinct_crossings"],
          row["capacity_deficit"],row["by_family"])
