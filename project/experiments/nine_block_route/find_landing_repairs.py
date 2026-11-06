"""Recover the exact accepted SRAM landing rectangles removed by rerouting."""
from pathlib import Path
import re
import sys

def footprints(definition):
    net = None
    result = set()
    route = re.compile(r"NEW metal3 \( (\d+) (\d+) \) RECT \( (-?\d+) (-?\d+) (-?\d+) (-?\d+) \)")
    with definition.open() as lines:
        for line in lines:
            if line.startswith("    - "):
                net = line.split()[1]
            if " RECT " not in line:
                continue
            m = route.search(line)
            if m:
                x,y,a,b,c,d = map(int,m.groups())
                result.add((net,x+a,y+b,x+c,y+d))
    return result

tsv, approved, routed, out = map(Path,sys.argv[1:])
original, candidate = footprints(approved),footprints(routed)
missing = []
for row in tsv.read_text().splitlines():
    _,_,net,*bounds = row.split("\t")
    key = (net,*map(int,bounds))
    assert key in original, row
    if key not in candidate:
        missing.append(row)
assert missing
out.write_text("\n".join(missing)+"\n")
print(len(missing),"accepted SRAM rectangles to restore")
