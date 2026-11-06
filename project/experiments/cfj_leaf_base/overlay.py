"""Write and independently check an upper-only coupon on true routed M10 terminals."""
import hashlib
import json
import os
from pathlib import Path
import pya

run = Path(os.environ["CFJ_OVERLAY_DIR"])
native_file = Path(os.environ["CFJ_NATIVE_GDS"])
links = json.loads((run/"cut-links.json").read_text())["links"]
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
if native.dbu != 0.0005:
    raise ValueError("unexpected native GDS DBU")
m10 = pya.Region(native.top_cell().begin_shapes_rec(native.find_layer(29,0)))
m10.merge()
layout = pya.Layout()
layout.dbu = native.dbu
top = layout.create_cell("CFJ_UPPER_COUPON")
layers = {11:(211,0),12:(213,0),110:(210,0),111:(212,0)}
expected = []
upper = run/"upper-only.gds"
used_columns = {}
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
    if any(ys[0]<stop+8400 and ys[1]>start-8400 for start,stop in spans):
        raise ValueError(f"fixture column overlaps another connection: {source}")
    spans.append(ys)
    for rect in (a,b):
        y=(rect[1]+rect[3])//2
        cut=pya.Box(x-2000,y-2000,x+2000,y+2000)
        if not (pya.Region(cut)-pya.Region(pya.Box(*rect))).is_empty() or not (pya.Region(cut)-m10).is_empty():
            raise ValueError(f"via10 lower landing missing at {source} -> {sink}")
        for layer in (11,110,111):
            top.shapes(layout.layer(*layers[layer])).insert(cut).set_property(1,source)
            expected.append((layers[layer],(cut.left,cut.bottom,cut.right,cut.top),source))
    strip=pya.Box(x-2000,ys[0]-2000,x+2000,ys[1]+2000)
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
if any(not regions[i].width_check(4000).is_empty() or not regions[i].space_check(4000).is_empty() for i in (11,12)):
    raise ValueError("upper metal width or spacing")
if any(not regions[i].space_check(4400).is_empty() for i in (110,111)):
    raise ValueError("upper cut spacing")
if any(not (regions[via]-regions[metal]).is_empty() for via,metal in [(110,11),(111,11),(111,12)]):
    raise ValueError("missing upper landing")
report=dict(nets=len(links), verified_via10=2*len(links), native_gds_sha256=sha(native_file), overlay_sha256=sha(upper),
            scope="separate native nets, real M10 pin/GDS containment, upper-only geometry; no RC or timing")
(run/"geometry.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
