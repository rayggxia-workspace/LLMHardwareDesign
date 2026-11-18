import pya,json,hashlib
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-v27-s-m9-guard-v2'
g=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.gds'
h=hashlib.sha256(g.read_bytes()).hexdigest()
assert h=='cc3f80b43858fb882d9d2d391edfd73b40921f3ccb221c6c15a2c69ea6702a58'
l=pya.Layout();l.read(str(g));assert l.dbu==.0001
roi=pya.Region(pya.Box(13580000,1090000,13650000,1160000))
actual=pya.Region(l.top_cell().begin_shapes_rec(l.layer(27,0)))&roi
a=pya.Region(pya.Box(2723800*5,223340*5,2725400*5,228140*5))
b=pya.Region(pya.Box(2720990*5,223340*5,2722590*5,224940*5))
assert (a-actual).is_empty() and (b-actual).is_empty(),'Expected actual M9 material missing'
assert (a&b).is_empty()
assert not a.separation_check(b,8000).is_empty()
assert a.separation_check(b,6050).is_empty()
guard=pya.Region(pya.Box(2722800*5,223340*5,2723000*5,224940*5))
assert (guard&actual).is_empty(),'Trial obstruction touches existing actual metal'
assert hashlib.sha256(g.read_bytes()).hexdigest()==h
result=dict(accepted=False,actual_gds_geometry_confirmed=True,source_gds_sha256=h,
            gap_um=.605,required_spacing_um=.8,guard_is_empty_actual_material=True,
            scope='Actual GDS confirms two separate M9 route materials and an empty virtual guard; actual ECO route/complete rules still pending')
(p/'gds-diagnostic.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
