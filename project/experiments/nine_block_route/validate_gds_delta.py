"""Confirm the repair changes exactly the accepted root M3 patch rectangles."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import pya

before, after, tsv, receipt = (Path(os.environ[name]) for name in
    ("MASK_BEFORE","MASK_AFTER","LANDING_PATCHES","MASK_RECEIPT"))
old, new = pya.Layout(), pya.Layout()
old.read(str(before))
new.read(str(after))
assert old.dbu == new.dbu == .0001
assert {c.name for c in old.each_cell()} == {c.name for c in new.each_cell()}
assert old.top_cell().name == new.top_cell().name
layer_ids = {(i.layer,i.datatype) for i in old.layer_infos()}
assert layer_ids == {(i.layer,i.datatype) for i in new.layer_infos()}
def instances(cell):
    return Counter((i.cell.name,t.mag,t.angle,t.is_mirror(),t.disp.x,t.disp.y)
        for i in cell.each_inst() for t in i.cell_inst.each_cplx_trans())

patches = Counter()
for row in tsv.read_text().splitlines():
    _,_,net,*coords = row.split("\t")
    patches[tuple(int(v)*5 for v in coords)+(net,)] += 1

def shape_key(shape):
    if shape.is_box():
        r=shape.box
        return (r.left,r.bottom,r.right,r.top,shape.property(1))
    return shape.to_s()

for c in old.each_cell():
    mapped = new.cell(c.name)
    assert instances(c)==instances(mapped), c.name
    for layer,datatype in sorted(layer_ids):
        left = Counter(map(shape_key,c.shapes(old.find_layer(layer,datatype)).each()))
        right = Counter(map(shape_key,mapped.shapes(new.find_layer(layer,datatype)).each()))
        if c.name == old.top_cell().name and (layer,datatype)==(15,0):
            assert right-left==patches and not left-right, (list((right-left).items())[:8], list(patches.items()))
        else:
            assert left==right, (c.name,layer,datatype)
def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            digest.update(chunk)
    return digest.hexdigest()

receipt.write_text(json.dumps(dict(passed=True, only_changed_mask="M3", placements_identical=True,
    patch_count=sum(patches.values()),before_sha256=sha(before),after_sha256=sha(after),
    repaired_nets=sorted({k[-1] for k in patches})),indent=2)+"\n")
