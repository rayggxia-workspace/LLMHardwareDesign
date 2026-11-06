"""Add two upper-metal legs for a native P VALID midpoint repeater."""
from pathlib import Path
import json
import re
import sys
from escape import Grid, to_dbu, to_grid

source, abstract, out = map(Path, sys.argv[1:])
out.mkdir()
spec = json.loads((source.parent / "inputs.json").read_text())
design = (source.parent / "coupon.def").read_text()
proof = json.loads(source.read_text())
grid = Grid(*(v // 4 for v in spec["die_um"]))
proof["routes"].pop("p_gate_valid")
pads = spec["macro_endpoint_rects_dbu"].pop("p_gate_valid")
for net, route in proof["routes"].items():
    grid.commit([(layer,to_grid(a),to_grid(b)) for layer,a,b in route["segments"]],
                [to_grid(p) for p in route["via11"]], net)

x, y = (n * 2000 for n in spec["positions_um"]["P0"])
left, right = [], []
lef = abstract.read_text()
for suffix in ("in", "out"):
    block = re.search(rf"^\s+PIN upper_valid_{suffix}\s*\n(.*?)^\s+END upper_valid_{suffix}\s*$", lef, re.M | re.S)[1]
    coords = re.search(r"LAYER metal10\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", block).groups()
    a,b,c,d = (round(float(v)*2000) for v in coords)
    (left if suffix=="in" else right).append([a+x,b+y,c+x,d+y])

targets={"p_gate_valid_pre": [pads[0],left[0]], "p_gate_valid_post": [right[0],pads[1]]}
spec["macro_endpoint_rects_dbu"].update(targets)
points={n:[to_grid(((a+c)//2,(b+d)//2)) for a,b,c,d in rs] for n,rs in targets.items()}
for net,ends in points.items():
    if not all(grid.legal_segment((11,p,p),net) for p in ends):
        raise ValueError(f"crowded native landing for {net}")
    grid.commit([(11,p,p) for p in ends], [], net)
for net,(a,b) in points.items():
    trials=[]
    for xx in range(2,grid.max_x-2):
        p,q=(xx,a[1]),(xx,b[1])
        if not grid.legal_via(p) or not grid.legal_via(q):
            continue
        segments=[(11,a,p),(12,p,q),(11,q,b)]
        if all(grid.legal_segment(s,net) for s in segments):
            length=sum(abs(s[0]-t[0])+abs(s[1]-t[1]) for _,s,t in segments)
            trials.append((length,abs(xx-(a[0]+b[0])/2),segments,[p,q]))
    if not trials:
        raise ValueError(f"could not route {net}")
    length,_,segments,vias=min(trials)
    grid.commit(segments,vias,net)
    proof["routes"][net] = dict(segments=[(m,to_dbu(p),to_dbu(q)) for m,p,q in segments],
        via11=[to_dbu(p) for p in vias],via10=[to_dbu(p) for p in (a,b)])
    print(net,length*4,"um")

design = design.replace(
    "- p_gate_valid ( P0 m_to_g_valid ) ( P0 g_from_m_valid ) + USE SIGNAL ;",
    "- p_gate_valid_pre ( P0 m_to_g_valid ) ( P0 upper_valid_in ) + USE SIGNAL ;\n"
    "- p_gate_valid_post ( P0 upper_valid_out ) ( P0 g_from_m_valid ) + USE SIGNAL ;")
design = design.replace("NETS 296 ;","NETS 297 ;")
(out/"coupon.def").write_text(design)
(out/"inputs.json").write_text(json.dumps(spec,indent=2))
(out/"route.json").write_text(json.dumps(proof,indent=2))
