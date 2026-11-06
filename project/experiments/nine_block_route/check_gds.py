"""Read back an upper-only GDS and check its overlay against actual native GDS."""
import hashlib
import json
import os
from pathlib import Path
import pya

run = Path(os.environ["COUPON_AUDIT"])
proof = json.loads((run/"route.json").read_text())
spec = json.loads((run/"inputs.json").read_text())
sources = json.loads((run/"gds-inputs.json").read_text())
layers = {10:(29,0), 11:(211,0), 12:(213,0), 110:(210,0), 111:(212,0)}
dbu = 0.0005
half = 2000
layout = pya.Layout()
layout.dbu = dbu
top = layout.create_cell("NINE_BLOCK_UPPER_COUPON")
expected=[]
def add(layer, a,b,net):
    pair = layers[layer]
    rect = (min(a[0],b[0])-half,min(a[1],b[1])-half,max(a[0],b[0])+half,max(a[1],b[1])+half)
    s=top.shapes(layout.layer(*pair)).insert(pya.Box(*rect))
    s.set_property(1,net)
    expected.append((pair,rect,net))
for net,entry in proof["routes"].items():
    for layer,a,b in entry["segments"]:
        add(layer,a,b,net)
    for p in entry["via10"]:
        add(110,p,p,net)
        add(11,p,p,net)
    for p in entry["via11"]:
        add(111,p,p,net)
        add(11,p,p,net)
        add(12,p,p,net)
gds=run/"upper-only.gds"
layout.write(str(gds))
read=pya.Layout()
read.read(str(gds))
assert read.dbu==dbu
top=read.top_cell()
regions={}
observed=[]
for k,pair in layers.items():
    index=read.find_layer(*pair)
    regions[k]=pya.Region()
    if index is None:
        continue
    for s in top.shapes(index).each():
        assert s.is_box()
        b=s.box
        observed.append((pair,(b.left,b.bottom,b.right,b.top),s.property(1)))
        regions[k].insert(b)
    regions[k].merge()
# GDS omits native metal altogether, including the via10 bottom shape.
assert set((info.layer,info.datatype) for info in read.layer_infos()) <= {layers[x] for x in (11,12,110,111)}
assert sorted(expected)==sorted(observed)
native=pya.Region()
receipt={}
for name,source in sources.items():
    leaf=pya.Layout()
    leaf.read(source)
    top_leaf=leaf.top_cell()
    layer=leaf.find_layer(*layers[10])
    assert layer is not None
    outline_layer=leaf.find_layer(235,0)
    assert outline_layer is not None, name
    outline=top_leaf.bbox(outline_layer)
    w,h=spec["sizes_um"][name[0]]
    assert outline.left==0 and outline.bottom==0 and abs(outline.width()*leaf.dbu-w)<dbu and abs(outline.height()*leaf.dbu-h)<dbu, (name,outline,leaf.dbu,w,h)
    shape=pya.Region(top_leaf.begin_shapes_rec(layer))
    x,y=spec["positions_um"][name]
    transform=pya.ICplxTrans(leaf.dbu/dbu,0,False,round(x/dbu),round(y/dbu))
    native+=shape.transformed(transform)
    receipt[name]=dict(source=source,dbu=leaf.dbu,native_m10_shape_count=shape.count())
native.merge()
checks={}
for k in (11,12):
    checks[f"M{k}_width"]=regions[k].width_check(4000).is_empty()
    checks[f"M{k}_spacing"]=regions[k].space_check(4000).is_empty()
for k in (110,111):
    checks[f"via{k-100}_spacing"]=regions[k].space_check(4400).is_empty()
missing = {}
for net, entry in proof["routes"].items():
    for x, y in entry["via10"]:
        cut = pya.Region(pya.Box(x-half,y-half,x+half,y+half))
        residual = cut - native
        if not residual.is_empty():
            missing.setdefault(net, []).append({"center_um": [x*dbu,y*dbu], "uncovered_um2": residual.area()*dbu**2})
checks["via10_lower_inside_real_native_m10"]=not missing
(run/"uncovered-via10.json").write_text(json.dumps(missing,indent=2))
checks["via10_upper_inside_m11"]=(regions[110]-regions[11]).is_empty()
checks["via11_lower_inside_m11"]=(regions[111]-regions[11]).is_empty()
checks["via11_upper_inside_m12"]=(regions[111]-regions[12]).is_empty()
checks["upper_only_no_native_mask_delta"]=regions[10].is_empty()
result=dict(passed=all(checks.values()), checks=checks, nets=len(proof["routes"]),
            source_native_gds=receipt, gds_bytes=gds.stat().st_size,
            sha256=hashlib.sha256(gds.read_bytes()).hexdigest())
(run/"klayout-receipt.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
if not result["passed"]:
    raise RuntimeError("research overlay geometry failed")
