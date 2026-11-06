"""Check the two native 70 nm M3 rules near every repaired landing."""
import json
import os
from pathlib import Path
import pya

source=Path(os.environ["CHECK_GDS"])
patches=Path(os.environ["CHECK_PATCHES"])
layout=pya.Layout()
layout.read(str(source))
top=layout.top_cell()
layer=layout.find_layer(15,0)
margin=round(1.0/layout.dbu)
spacing=round(.07/layout.dbu)
results=[]
for row in patches.read_text().splitlines():
    bank,pin,net,*coords=row.split("\t")
    a,b,c,d=(round(int(v)/2000/layout.dbu) for v in coords)
    crop=pya.Box(a-margin,b-margin,c+margin,d+margin)
    roi=pya.Box(a-spacing,b-spacing,c+spacing,d+spacing)
    geometry=(pya.Region(top.begin_shapes_rec_overlapping(layer,crop)) & pya.Region(crop)).merged()
    rules={"METAL3.1":geometry.width_check(spacing), "METAL3.2":geometry.space_check(spacing)}
    results.append(dict(bank=bank,pin=pin,net=net,
        markers={key:sum(roi.overlaps(e.bbox()) for e in value.each()) for key,value in rules.items()}))
Path(os.environ["CHECK_RESULT"]).write_text(json.dumps(results,indent=2)+"\n")
assert not any(n for row in results for n in row["markers"].values()),results
