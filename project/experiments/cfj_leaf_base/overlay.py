"""Write and independently check an upper-only coupon on true routed M10 terminals."""
import hashlib
import json
import math
import os
from pathlib import Path
import pya

run = Path(os.environ["CFJ_OVERLAY_DIR"])
native_file = Path(os.environ["CFJ_NATIVE_GDS"])
cut_plan = json.loads((run/"cut-links.json").read_text())
links = cut_plan["links"]
technology = json.loads((Path(__file__).resolve().parents[1]/"block_v1/technology-2um-v1.json").read_text())
g = technology["geometry_um"]
e = technology["electrical"]
pins = {}
for line in (run/"endpoints.tsv").read_text().splitlines():
    name, direction, native_net, *rect = line.split("\t")
    if name in pins:
        raise ValueError(f"{name}: expected a single M10 landing")
    pins[name] = (direction, native_net, tuple(map(int, rect)))

def sha(path):
    with path.open("rb") as f:
        digest = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

native = pya.Layout()
native.read(str(native_file))
odb_per_um = int((run/"endpoints.tsv.dbu").read_text())

def u(um):
    value = um/native.dbu
    integer = round(value)
    if not math.isclose(value, integer, abs_tol=1e-6):
        raise ValueError(f"{um} um cannot be represented in the native GDS grid")
    return integer

pins = {name:(direction, net, tuple(u(value/odb_per_um) for value in rect))
        for name,(direction,net,rect) in pins.items()}
half = u(g["width"]/2)
min_center = u(g["cut_width"]+g["cut_spacing"])
native_top = native.top_cell()
m10 = pya.Region(native_top.begin_shapes_rec(native.find_layer(29,0)))
m10.merge()
layout = pya.Layout()
layout.dbu = native.dbu
top = layout.create_cell("CFJ_UPPER_COUPON")
layers = {11:(211,0),12:(213,0),110:(210,0),111:(212,0)}
expected = []
upper = run/"upper-only.gds"
used_columns = {}
connections = []
for source, sink in links:
    d0,n0,a = pins[source]
    d1,n1,b = pins[sink]
    if d0!="OUTPUT" or d1!="INPUT" or n0==n1:
        raise ValueError(f"invalid or already connected native boundary {source} -> {sink}")
    x = (a[0]+a[2])//2
    if (b[0]+b[2])//2 != x:
        raise ValueError(f"fixture landings are not aligned: {source}")
    ys = sorted([(a[1]+a[3])//2,(b[1]+b[3])//2])
    spans = used_columns.setdefault(x, [])
    if any(ys[0]<stop+min_center and ys[1]>start-min_center for start,stop in spans):
        raise ValueError(f"fixture column overlaps another connection: {source}")
    spans.append(ys)
    for name, rect in ((source,a),(sink,b)):
        actual = tuple((rect[i]+rect[i+2])*native.dbu/2 for i in (0,1))
        if any(not math.isclose(v, w, abs_tol=native.dbu/2)
               for v,w in zip(actual, cut_plan["positions_um"][name])):
            raise ValueError(f"{name}: final routed pin center differs from planned center")
    length = (ys[1]-ys[0])*native.dbu
    c_per_um = 0.0088541878128 * e["relative_permittivity"] * (
        g["width"]/g["dielectric_gap"] + 2*g["thickness"]/g["spacing"])
    r = e["sheet_resistance_ohm"]*length/g["width"] + 4*e["via_resistance_ohm"]
    connections.append(dict(source=source, sink=sink, source_native_net=n0, sink_native_net=n1,
        wire_um=length, rc={name:dict(r_ohm=r*scale, c_ff=c_per_um*length*scale)
                           for name,scale in e["estimate_variants"].items()}))
    for rect in (a,b):
        y=(rect[1]+rect[3])//2
        cut=pya.Box(x-half,y-half,x+half,y+half)
        if not (pya.Region(cut)-pya.Region(pya.Box(*rect))).is_empty() or not (pya.Region(cut)-m10).is_empty():
            raise ValueError(f"via10 lower landing missing at {source} -> {sink}")
        for layer in (11,110,111):
            top.shapes(layout.layer(*layers[layer])).insert(cut).set_property(1,source)
            expected.append((layers[layer],(cut.left,cut.bottom,cut.right,cut.top),source))
    strip=pya.Box(x-half,ys[0]-half,x+half,ys[1]+half)
    top.shapes(layout.layer(*layers[12])).insert(strip).set_property(1,source)
    expected.append((layers[12],(strip.left,strip.bottom,strip.right,strip.top),source))
layout.write(str(upper))

check = pya.Layout()
check.read(str(upper))
observed = []
regions={}
for k,pair in layers.items():
    shapes=check.top_cell().shapes(check.find_layer(*pair))
    regions[k]=pya.Region()
    for shape in shapes.each():
        box=shape.box
        observed.append((pair,(box.left,box.bottom,box.right,box.top),shape.property(1)))
        regions[k].insert(box)
    regions[k].merge()
if sorted(expected)!=sorted(observed) or len(check.layer_infos())!=len(layers):
    raise ValueError("GDS readback differs or contains native shapes")
if any(not regions[i].width_check(u(g["width"])).is_empty() or not regions[i].space_check(u(g["spacing"])).is_empty() for i in (11,12)):
    raise ValueError("upper metal width or spacing")
if any(not regions[i].space_check(u(g["cut_spacing"])).is_empty() for i in (110,111)):
    raise ValueError("upper cut spacing")
if any(not (regions[via]-regions[metal]).is_empty() for via,metal in [(110,11),(111,11),(111,12)]):
    raise ValueError("missing upper landing")
# Preserve the original input file and instantiate an upper-only child in a
# separately emitted GDS. The native layer hierarchy is untouched.
native.read(str(upper))
native_top.insert(pya.CellInstArray(native.cell("CFJ_UPPER_COUPON").cell_index(), pya.Trans()))
combined = run/"combined-research.gds"
native.write(str(combined))
(run/"binding.json").write_text(json.dumps(dict(rule=technology["rule_id"],
    rc_model=e["model"], connections=connections),indent=2)+"\n")
report=dict(nets=len(links), verified_via10=2*len(links), native_gds_sha256=sha(native_file), overlay_sha256=sha(upper),
            combined_sha256=sha(combined),
            scope="separate native nets, real M10 pin/GDS containment and geometry, research wire RC; no stitched STA")
(run/"geometry.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
