"""Report route artifacts; keep native-mask and endpoint tests separate from DRT."""
import json
from pathlib import Path
import re
import sys

def audit(case):
    inputs = json.loads((case / "inputs.json").read_text())
    expected = inputs["macro_endpoint_rects_dbu"]
    report = {"case": case.name, "net_count": len(expected), "die_um": inputs["die_um"]}
    log = (case / "route.log").read_text(errors="replace")
    report["macro_no_access"] = [int(n) for n in re.findall(r"#macroNoAp\s*=\s*(\d+)", log)]
    report["errors"] = re.findall(r"^\[ERROR [^\n]+", log, re.M)
    drc = case / "drc.rpt"
    report["router_drc_empty"] = not drc.read_text().strip() if drc.exists() else None
    final = case / "routed.def"
    if not final.exists():
        return report
    text = final.read_text()
    nets = re.search(r"^NETS\s+\d+\s*;(.*?)^END NETS", text, re.S | re.M)[1]
    routed, bad_endpoints, native = [], [], []
    for name, entry in re.findall(r"^\s*-\s+(\S+)\s+(.*?);", nets, re.M | re.S):
        paths = re.findall(r"\b(?:ROUTED|NEW)\s+(metal\d+)\s+(.*?)(?=\s+NEW\s|$)", entry, re.S)
        if paths:
            routed.append(name)
        landings = []
        for layer, path in paths:
            if int(layer[5:]) > 10:
                continue
            match = re.fullmatch(r"\s*\(\s*(\d+)\s+(\d+)\s*\)\s+BV1_via10\s*", path)
            if layer != "metal10" or not match:
                native.append(name)
                continue
            landings.append(tuple(map(int, match.groups())))
        rects = expected[name]
        if len(landings) != len(rects) or any(
            sum(a+2000 <= x <= c-2000 and b+2000 <= y <= d-2000 for x,y in landings) != 1
            for a,b,c,d in rects
        ):
            bad_endpoints.append(name)
    report.update(routed_nets=len(routed), p_routed_nets=sum(n.startswith("p_gate") for n in routed),
                  absent_nets=sorted(set(expected)-set(routed)), native_shape_suspects=sorted(set(native)),
                  endpoint_enclosure_suspects=bad_endpoints)
    return report

for folder in sys.argv[1:]:
    print(json.dumps(audit(Path(folder))))
