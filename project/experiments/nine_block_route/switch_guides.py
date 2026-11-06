"""Prepare a two-layer detailed-route comparison for the same real endpoints."""

import json
from pathlib import Path
import re
import sys


case, root, switch = (Path(value).resolve() for value in sys.argv[1:4])
spec = json.loads((case / "inputs.json").read_text())
bindings = json.loads((case / "case-binding.json").read_text())
required = {kind: {"VDD", "VSS"} for kind in "PUCFJT"}
for terminals in bindings["endpoints"].values():
    for name, pin in terminals:
        required[name[0]].add(pin)

# Keep the master geometry and obstructions while avoiding pin-access work
# on thousands of unconnected terminals. Actual GDS remains the source for
# the independent landing check.
def route_lef(kind, original):
    text = original.read_text()
    pattern = r"^\s+PIN (\S+)\s*\n(.*?)^\s+END \1\s*$"
    seen = set()

    def retain(match):
        name = match[1]
        if name in required[kind] or re.search(r"USE\s+(POWER|GROUND)\s*;", match[2]):
            seen.add(name)
            return match[0]
        return ""

    filtered = re.sub(pattern, retain, text, flags=re.M | re.S)
    absent = required[kind]-{"VDD", "VSS"}-seen
    if absent:
        raise ValueError(f"Missing required routing pins for {kind}: {sorted(absent)}")
    path = case/f"{kind}.lef"
    path.write_text(filtered)
    return path


lefs = [route_lef(k, root/(k+".lef")) for k in "PUCFJ"]+[route_lef("T", switch)]
grid = 120000  # 60 um routing-guide tile at 2,000 DBU/um.
limit_x, limit_y = (value*2000 for value in spec["die_um"])


def box(a, b, layer, padding=1):
    x, xx = sorted((a[0]//grid, b[0]//grid))
    y, yy = sorted((a[1]//grid, b[1]//grid))
    return f"{max(0,x-padding)*grid} {max(0,y-padding)*grid} " \
        f"{min(limit_x,(xx+1+padding)*grid)} {min(limit_y,(yy+1+padding)*grid)} {layer}"


lines = []
for i,(net,rects) in enumerate(spec["macro_endpoint_rects_dbu"].items()):
    p,q = [((xl+xh)//2,(yl+yh)//2) for xl,yl,xh,yh in rects]
    x = max(grid,min(limit_x-grid,(p[0]+q[0])//2 + ((i % 29)-14)*grid))
    r,s = (x,p[1]),(x,q[1])
    lines.extend([net, "(", box(p,r,"metal11"), box(r,s,"metal12"), box(s,q,"metal11"),
                  box(p,p,"metal10",0), box(q,q,"metal10",0), ")"])
(case/"upper.guide").write_text("\n".join(lines)+"\n")
(case/"upper.tcl").write_text("\n".join([
    f"read_lef {{{root/'research12.tech.lef'}}}",
    *(f"read_lef {{{lef}}}" for lef in lefs),
    "read_def coupon.def",
    "source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl",
    f"source {{{root/'new_tracks.tcl'}}}",
    "set_thread_count $::env(SLURM_CPUS_PER_TASK)",
    "set_routing_layers -signal metal11-metal12",
    "set_macro_extension 0",
    "pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10",
    "read_guides upper.guide",
    "detailed_route -droute_end_iter 24 -output_drc drc.rpt -output_guide_coverage coverage.csv "
    "-via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10",
    "write_db routed.odb",
    "write_def routed.def",
    "",
]))
