from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-upper-spacing-guard-v5';p=r/'audit/C-v27-r-fullguard';p.mkdir(exist_ok=False)
s=(old/'export.tcl').read_text().replace('C-v20-native-clock4','C-v27-joint-e20-h30').replace('{r_stream_local local_s_base block_v2_g block_v2_e_compact}','{r_stream_local}');(p/'export.tcl').write_text(s);(p/'hook.tcl').write_bytes((old/'hook.tcl').read_bytes())
(p/'derive.py').write_text('''from pathlib import Path
import pya,json,hashlib
p=Path.cwd();r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');g=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.gds';l=pya.Layout();l.read(str(g));assert l.dbu==0.0001;c=l.cell('r_stream_local');assert c;regions={};size=None
for s in (p/'master-geometry.tsv').read_text().splitlines():
 a=s.split('\\t')
 if a[0]=='MASTER':assert a[1]=='r_stream_local';size=list(map(int,a[2:]));continue
 k,n,layer,*v=a;regions.setdefault((k,layer),pya.Region()).insert(pya.Box(*[int(z)*5 for z in v[:4]]))
rows=[];stats=[]
for layer,num in [('metal9',27),('via9',28)]:
 actual=pya.Region(c.begin_shapes_rec(l.layer(num,0))).merged();obs=regions.get(('OBS',layer),pya.Region());pins=regions.get(('PIN',layer),pya.Region());assert pins.is_empty(),('MPin on guard layer requires separate reviewed access design',layer)
 keepout=((actual.sized(4000)-obs)&pya.Region(pya.Box(0,0,size[0]*5,size[1]*5))).merged();rec=pya.Region();count=0
 for poly in keepout.decompose_trapezoids_to_region().each():
  b=poly.bbox();assert b.area()==poly.area();v=[b.left,b.bottom,b.right,b.top];assert all(z%5==0 for z in v);rows.append(('r_stream_local',layer,*[z//5 for z in v]));rec.insert(b);count+=1
 assert (rec^keepout).is_empty();stats.append(dict(layer=layer,rectangles=count,added_keepout_um2=keepout.area()*1e-8))
(p/'keepout.tsv').write_text(''.join('\\t'.join(map(str,x))+'\\n' for x in rows));(p/'ripup-nets.txt').write_text('# R ALL non-PG nets must have access regenerated; enumerate from actual candidate, not fixed net list.\\n');v=dict(scope='R entire actual M9 and via9 material plus conservative 0.4um routing keepout, subtract installed OBS. No same-layer MPins exist; M10 pins unchanged but actual via-access must still be probed. Not physical metal or timing qualification.',rectangles=len(rows),stats=stats,source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [g,p/'master-geometry.tsv',p/'keepout.tsv',Path(__file__)]});(p/'receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
''')
s=(old/'run.sbatch').read_text().replace('C-upper-spacing-guard-v5','C-v27-r-fullguard');(p/'run.sbatch').write_text(s)
