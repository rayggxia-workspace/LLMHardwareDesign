import pya,json,hashlib
from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1');src=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds')
a=pya.Layout();a.read(str(src));b=pya.Layout();b.read(str(p/'patched.gds'));assert a.dbu==b.dbu==.0001
box=pya.Box(13900000,5780000,13960000,5830000)
a10=pya.Region(a.top_cell().begin_shapes_rec(a.layer(29,0)))&pya.Region(box)
b10=pya.Region(b.top_cell().begin_shapes_rec(b.layer(29,0)))&pya.Region(box)
expected=pya.Region(pya.Box(13930950,5804700,13932950,5810700))
added=b10-a10;removed=a10-b10
assert removed.is_empty();assert (added^expected).is_empty(),str(added)
inner=pya.Region(pya.Box(13930000,5795000,13935000,5815000))
def markers(r):
 q=r.space_check(8000);n=r.notch_check(8000)
 return dict(space=[str(x) for x in q.each() if not (pya.Region(x.bbox())&inner).is_empty()],notch=[str(x) for x in n.each() if not (pya.Region(x.bbox())&inner).is_empty()])
pre=markers(a10);post=markers(b10)
assert not post['space'] and not post['notch'],post
# Check all other local layers against actual original streamout.
for l in a.layer_infos():
 if (l.layer,l.datatype)==(29,0):continue
 x=pya.Region(a.top_cell().begin_shapes_rec(a.layer(l)))&pya.Region(box)
 y=pya.Region(b.top_cell().begin_shapes_rec(b.layer(l)))&pya.Region(box)
 assert (x^y).is_empty(),str(l)
r=dict(passed=True,scope='Actual DEF-derived GDS local geometric delta and unchanged M10 0.8um spacing/notch threshold; not full backend acceptance',added_area_um2=added.area()*a.dbu*a.dbu,removed_area_um2=removed.area()*a.dbu*a.dbu,before=pre,after=post,other_local_layers_equal=True,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src,p/'patched.gds',p/'patched.def',p/'patched.odb']})
(p/'gds-local-receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
