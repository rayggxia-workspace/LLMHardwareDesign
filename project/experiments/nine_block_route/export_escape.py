"""Export a verified geometry proposal as a DEF using the coupon's placements."""
import json
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
result = json.loads(path.read_text())
case = path.parent
proof = json.loads(path.with_name(path.stem+"-audit.json").read_text())
if not proof["passes_coupon_geometry"]:
    raise SystemExit("Only independently checked complete geometry may be exported.")
text = (case/"coupon.def").read_text()
lines = text.splitlines()
in_nets = False
def point(p):
    return f"( {p[0]} {p[1]} )"
for i,line in enumerate(lines):
    if line.startswith("NETS "):
        in_nets = True
    elif line == "END NETS":
        in_nets = False
    elif in_nets and line.startswith("- "):
        net = line.split()[1]
        entry = result["routes"][net]
        shapes = [f"metal{layer} {point(a)} {point(b)}" for layer,a,b in entry["segments"] if a!=b]
        for via in (10,11):
            shapes.extend(f"metal{via} {point(p)} BV1_via{via}" for p in entry[f"via{via}"])
        lines[i] = re.sub(r"\s*;\s*$"," + ROUTED "+" NEW ".join(shapes)+" ;",line)
out=path.with_suffix(".def")
out.write_text("\n".join(lines)+"\n")
