from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-upper-metal-guard-v2'
(p/'derive-r-keepout.py').write_text('''from pathlib import Path
import pya,json,hashlib
p=Path.cwd();r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');g=r/'cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds';l=pya.Layout();l.read(str(g));assert l.dbu==0.0001
loc=json.loads((r/'audit/C-main-clock4-physical-v1/non-dot-upper-net-candidates.json').read_text());points=[m for m in loc if m['macro']==['r_stream_local']];assert len(points)==12
clip=pya.Region()
for m in points:
 a,b,c,d=m['bbox_um'];clip.insert(pya.Box(round((a-72-1)*10000),round((b-72-1)*10000),round((c-72+1)*10000),round((d-72+1)*10000)))
actual=pya.Region(l.cell('r_stream_local').begin_shapes_rec(l.layer(27,0))).merged();obs=pya.Region();pins=pya.Region()
for s in (p/'master-geometry.tsv').read_text().splitlines():
 a=s.split('\\t')
 if len(a)<7 or a[1]!='r_stream_local' or a[2]!='metal9':continue
 box=pya.Box(*[int(v)*5 for v in a[3:7]])
 if a[0]=='OBS':obs.insert(box)
 elif a[0]=='PIN':pins.insert(box)
assert pins.is_empty()
keepout=((actual&clip).sized(4000)-obs).merged();assert (keepout&pins).is_empty();rows=[];recovered=pya.Region()
for poly in keepout.decompose_trapezoids_to_region().each():
 b=poly.bbox();assert b.area()==poly.area();v=[b.left,b.bottom,b.right,b.top];assert all(z%5==0 for z in v);rows.append(('r_stream_local','metal9',*[z//5 for z in v]));recovered.insert(b)
assert (recovered^keepout).is_empty();(p/'r-m9-keepout.tsv').write_text(''.join('\\t'.join(map(str,x))+'\\n' for x in rows));v=dict(scope='Conservative localized 0.4um routing keepout expansion of actual R M9 metal at six observed foreign signal near-spacing sites. Not new physical metal. No M9 macro pins exist; leaf GDS and pins unchanged.',rectangles=len(rows),added_keepout_um2=keepout.area()*1e-8,target_parent_nets=sorted({h['net'] for m in points for h in m['hits']}),source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [g,p/'master-geometry.tsv',p/'r-m9-keepout.tsv',Path(__file__)]});(p/'r-keepout-receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
''')
s=(p/'run.sbatch').read_text().replace('openroad -no_init -exit export.tcl > export.log 2>&1; klayout -b -r derive.py > derive.log 2>&1','klayout -b -r derive-r-keepout.py > r-keepout.log 2>&1');(p/'r-keepout.sbatch').write_text(s)
