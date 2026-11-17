"""Exact recursive top-level polygon-material comparison; no cell-name assumptions."""
import pya,os,json,hashlib
from pathlib import Path
paths=[Path(os.environ[k]).resolve() for k in ('GDS_COMPARE_A','GDS_COMPARE_B')];out=Path(os.environ['GDS_COMPARE_OUT']).resolve()
layouts=[]
for p in paths:
 l=pya.Layout();l.read(str(p));layouts.append(l)
assert layouts[0].dbu==layouts[1].dbu
layers=sorted(set((x.layer,x.datatype) for l in layouts for x in l.layer_infos()));rows=[]
for n,d in layers:
 regions=[pya.Region(l.top_cell().begin_shapes_rec(l.layer(n,d))) for l in layouts]
 diff=regions[0]^regions[1]
 rows.append(dict(layer=n,datatype=d,equal=diff.is_empty(),xor_area_um2=diff.area()*layouts[0].dbu**2,xor_bbox=str(diff.bbox()) if not diff.is_empty() else None))
 print(json.dumps(rows[-1]),flush=True)
r=dict(passed=all(x['equal'] for x in rows),scope='All GDS layer/datatype recursive top polygon material symmetric difference, including actual vias and PG, excluding text metadata',dbu_um=layouts[0].dbu,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},layers=rows)
out.write_text(json.dumps(r,indent=2));assert r['passed']
