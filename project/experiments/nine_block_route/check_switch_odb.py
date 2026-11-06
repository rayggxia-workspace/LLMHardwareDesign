"""Verify detailed-router geometry independently from OpenDB rectangle records."""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path

import pya


case = Path(os.environ["QWEN_CHECK_CASE"])
run = Path(os.environ["QWEN_CHECK_RUN"])
spec = json.loads((case/"inputs.json").read_text())
expected = spec["macro_endpoint_rects_dbu"]
sources = json.loads((case/"gds-inputs.json").read_text())
if "QWEN_PROTECTED_GDS" in os.environ:
    sources["T0"] = os.environ["QWEN_PROTECTED_GDS"]
layers = {"metal11": (211,0), "metal12": (213,0), "via10": (210,0), "via11": (212,0)}
geometry = defaultdict(lambda: defaultdict(set))
native_additions = defaultdict(set)
errors = []
aliases = {}
with (run/"wire-rectangles.tsv").open() as handle:
    header = next(handle).strip()
    if not header.endswith("dbu_per_um=2000"):
        raise ValueError(f"Unexpected OpenDB geometry units: {header}")
    for line in handle:
        if line.startswith("# NET "):
            _,_,alias,name = line.split()
            aliases[alias] = bytes.fromhex(name).decode()
            continue
        alias, layer, kind, *coords = line.strip().split("\t")
        if kind not in ("wire", "wire-via"):
            continue
        net = aliases[alias]
        rect = tuple(map(int,coords))
        if layer in layers:
            geometry[net][layer].add(rect)
            if kind == "wire":
                x0,y0,x1,y1 = rect
                if (layer == "metal11" and x1-x0 < y1-y0) or (layer == "metal12" and y1-y0 < x1-x0):
                    errors.append([net, layer, "wrong-way shape", rect])
        elif layer == "metal10" and kind == "wire-via":
            native_additions[net].add(rect)
        else:
            errors.append([net, layer, "native wire outside the upper overlay", rect])

if set(geometry) != set(expected):
    errors.append(["net coverage", sorted(set(expected)-set(geometry)), sorted(set(geometry)-set(expected))])

dbu = .0005
lower = pya.Region()
for name,source in sources.items():
    original = pya.Layout()
    original.read(source)
    layer = original.find_layer(29,0)
    if layer is None:
        raise ValueError(f"No native M10 found for {name}")
    x,y = spec["positions_um"][name]
    shapes = pya.Region(original.top_cell().begin_shapes_rec(layer))
    lower += shapes.transformed(pya.ICplxTrans(original.dbu/dbu,0,False,round(x/dbu),round(y/dbu)))
lower.merge()


def inside(a,b):
    return b[0] <= a[0] <= a[2] <= b[2] and b[1] <= a[1] <= a[3] <= b[3]


def connected(net, boxes, pin_rects):
    nodes = {}
    links = defaultdict(set)
    for layer in ("metal11","metal12"):
        group = pya.Region()
        for rect in boxes[layer]:
            group.insert(pya.Box(*rect))
        nodes[layer] = [pya.Region(poly) for poly in group.merged().each()]

    def attach(cut, layer):
        area = pya.Region(pya.Box(*cut))
        return [(layer,i) for i,piece in enumerate(nodes[layer]) if (area-piece).is_empty()]

    def link(a,b):
        links[a].add(b)
        links[b].add(a)

    cuts10 = boxes["via10"]
    if len(cuts10) != len(pin_rects) or any(sum(inside(cut,p) for cut in cuts10)!=1 for p in pin_rects):
        errors.append([net,"via10-to-M10 pin coverage"])
    for cut in cuts10:
        if not (pya.Region(pya.Box(*cut))-lower).is_empty():
            errors.append([net,"via10 outside actual native M10",cut])
        a = attach(cut,"metal11")
        if len(a)!=1:
            errors.append([net,"via10 not enclosed by M11",cut])
        else:
            link(("M10",cut),a[0])
    for rect in native_additions[net]:
        if not any(inside(rect,p) for p in pin_rects):
            errors.append([net,"via10 enclosure outside native pin",rect])
    for cut in boxes["via11"]:
        a,b = attach(cut,"metal11"),attach(cut,"metal12")
        if len(a)==len(b)==1:
            link(a[0],b[0])
        else:
            errors.append([net,"via11 enclosure",cut])

    all_nodes = {("M10",cut) for cut in cuts10}
    all_nodes.update((layer,i) for layer,regions in nodes.items() for i in range(len(regions)))
    if all_nodes:
        todo = [next(iter(all_nodes))]
        seen = set(todo)
        while todo:
            for nxt in links[todo.pop()]-seen:
                seen.add(nxt)
                todo.append(nxt)
        if seen == all_nodes and len(cuts10)==len(pin_rects):
            return True
    errors.append([net,"disconnected upper geometry"])
    return False


reached = sum(connected(net, geometry[net], pins) for net,pins in expected.items())
layout = pya.Layout()
layout.dbu = dbu
top = layout.create_cell("QWEN_SWITCH_UPPER_ONLY")
for layer,pair in layers.items():
    all_boxes = []
    region = pya.Region()
    for net,by_layer in geometry.items():
        for rect in by_layer[layer]:
            box = pya.Box(*rect)
            obj = top.shapes(layout.layer(*pair)).insert(box)
            obj.set_property(1,net)
            region.insert(box)
            all_boxes.append((rect,net))
            if layer.startswith("via") and (box.width()!=4000 or box.height()!=4000):
                errors.append([layer,net,"incorrect via dimensions",rect])
    if layer.startswith("metal") and not region.width_check(4000).is_empty():
        errors.append([layer,"2 um width"])
    # Region checks apply to merged shapes. Compare labeled rectangles as
    # well so a short between different nets cannot disappear in a merge.
    gap = 4400 if layer.startswith("via") else 4000
    active = []
    for (x,y,xx,yy),net in sorted(all_boxes):
        active = [(rect,n) for rect,n in active if rect[2]+gap > x]
        for (a,b,aa,bb),other in active:
            if other == net and layer.startswith("metal"):
                continue
            if max(0,x-aa,a-xx)**2 + max(0,y-bb,b-yy)**2 < gap*gap:
                errors.append([layer,net,other,"short or spacing",(x,y,xx,yy),(a,b,aa,bb)])
        active.append(((x,y,xx,yy),net))

out = run/"upper-only.gds"
layout.write(str(out))
readback = pya.Layout()
readback.read(str(out))
allowed = set(layers.values())
if any((info.layer,info.datatype) not in allowed for info in readback.layer_infos()):
    errors.append(["unexpected layer in upper-only GDS"])
for layer,pair in layers.items():
    idx = readback.find_layer(*pair)
    observed = set()
    if idx is not None:
        for shape in readback.top_cell().shapes(idx).each():
            b = shape.bbox()
            observed.add((shape.property(1),(b.left,b.bottom,b.right,b.top)))
    wanted = {(net,r) for net,ls in geometry.items() for r in ls[layer]}
    if observed != wanted:
        errors.append([layer,"GDS rectangle/net readback mismatch"])

receipt = dict(passed=not errors and reached==len(expected), requested=len(expected), reached=reached,
               errors=errors, upper_gds_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(run/"independent-upper.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({k:v for k,v in receipt.items() if k!="errors"}), "errors", len(errors))
if not receipt["passed"]:
    raise SystemExit("upper geometry failed")
