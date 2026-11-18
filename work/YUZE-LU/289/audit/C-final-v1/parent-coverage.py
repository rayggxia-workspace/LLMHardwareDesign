import pya,json,re,hashlib,sys,os
from pathlib import Path
from decimal import Decimal
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');model=Path(os.environ['C_MODEL_DIR']);out=model/'parent-abstract';raw=model/'cfj_group_c_memory_legacy.lef';parent=out/'cfj_group_c_memory_legacy.lef';gds=Path(os.environ['C_GDS'])
sys.path.insert(0,str(model));from compare_lef import parse
old,new=map(parse,(raw,parent));assert old['size']==new['size'] and old['pins']==new['pins'] and old['terms']==new['terms']
for layer in ('metal7','metal8','metal9','metal10'):assert sorted(old['obs'].get(layer,[]))==sorted(new['obs'].get(layer,[])),layer
for layer in ('metal1','metal2','metal3','metal4','metal5','metal6'):
 assert len(new['obs'][layer])==1;box=new['obs'][layer][0]
 for q in old['obs'][layer]:assert box[0]<=q[0] and box[1]<=q[1] and box[2]>=q[2] and box[3]>=q[3]
obs=parent.read_text().split('\n  OBS\n')[1];cuts={};current=None
for line in obs.splitlines():
 a=line.strip().replace(';','').split()
 if not a:continue
 if a[0]=='LAYER':current=a[1]
 elif a[0]=='RECT' and current.startswith('via'):
  vals=[Decimal(x)*10000 for x in a[1:]];assert all(x==int(x) for x in vals);cuts.setdefault(current,set()).add(tuple(map(int,vals)))
lay=pya.Layout();lay.read(str(gds));assert lay.dbu==.0001
counts={}
for name,n in (('via6',22),('via7',24),('via8',26),('via9',28)):
 shapes=pya.Region(lay.top_cell().begin_shapes_rec(lay.layer(n,0)));expected={(b.left,b.bottom,b.right,b.top) for b in (poly.bbox() for poly in shapes.each())}
 assert expected==cuts[name],(name,len(expected),len(cuts[name]));counts[name]=len(expected)
files=[raw,parent,gds,out/'model-import-receipt.json',Path(__file__)]
v=dict(passed=True,pins_die_direction_exact=True,upper_metal_obs_exact=True,lower_metal_obs_conservatively_covers_raw=True,cut_obs_exact_actual_gds_bounding_rectangles=counts,scope='Separate routing-safe parent abstract: original raw exported model retained, original bloat0 algorithm plus conservative M1–M6 cover and exact actual hierarchical via6–9 bounding rectangles; no physical layout change or new nominal STA requirement.',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'obstruction-coverage.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
