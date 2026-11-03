"""Read-only attribution of original continuous bbox demand, no gate changes."""
from pathlib import Path
import subprocess,shlex,json
q=r'''from pathlib import Path
import json,hashlib,time,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';gp=c/'topology/boundary-graph.json';g=json.loads(gp.read_text());parent={n:n for n in g['instances']};parent.update({r['instance']:r['source_instance']for r in g['boundary_links']['links']});reports=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for seed in [1702,1970]:
 path=c/'cap-capacity-candidates'/str(seed)/'placement.json';d=json.loads(path.read_text());nx=d['width_um']/4;ny=d['height_um']/4;totals=collections.Counter();count=collections.Counter();layers={k:[[[0.]*16 for _ in range(16)]for _ in range(2)]for k in ['within','between','PG']};contributions=collections.defaultdict(list)
 for name,ends in d['terminals'].items():
  if name.startswith('net_PG_'):category='PG'
  else:
   row=g['connections'][name[4:]];ids={parent.get(e['instance'],'TOP')for e in[row['driver'],*row['sinks']]};category='within'if len(ids)==1 else'between'
  xs=[p[0]for p in ends];ys=[p[1]for p in ends];x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);dx=x1-x0;dy=y1-y0;totals[category]+=dx+dy;count[category]+=1
  if not dx and not dy:continue
  if not dx:x0-=.5;x1+=.5
  if not dy:y0-=.5;y1+=.5
  area=(x1-x0)*(y1-y0);xa=max(0,min(15,int(x0*16/nx)));xb=max(0,min(15,int(x1*16/nx)));ya=max(0,min(15,int(y0*16/ny)));yb=max(0,min(15,int(y1*16/ny)))
  for x in range(xa,xb+1):
   xx=max(0,min(x1,(x+1)*nx/16)-max(x0,x*nx/16))
   for y in range(ya,yb+1):
    yy=max(0,min(y1,(y+1)*ny/16)-max(y0,y*ny/16));fraction=xx*yy/area/(nx*ny/256);h=dx*fraction;v=dy*fraction;layers[category][0][x][y]+=h;layers[category][1][x][y]+=v
    if h or v:contributions[(x,y)].append(dict(net=name,category=category,h=h,v=v))
 top=sorted([(sum(layers[k][l][x][y]for k in layers),l,x,y)for l in [0,1]for x in range(16)for y in range(16)],reverse=True)[:8];hotspots=[]
 for value,l,x,y in top:
  hotspots.append(dict(layer=l,tile=[x,y],density=value,by_category={k:layers[k][l][x][y]for k in layers},top_contributing_nets=sorted(contributions[(x,y)],key=lambda r:r['h'if l==0 else'v'],reverse=True)[:12]))
 reports.append(dict(seed=seed,placement=str(path),placement_sha256=sha(path),net_count=dict(count),bbox_wire_grid_length=dict(totals),hotspots=hotspots))
print(json.dumps(dict(captured_at=time.time(),graph=str(gp),graph_sha256=sha(gp),reports=reports,whole_system_qualified=False,scope='Read-only continuous uniform-bbox demand attribution by actual fixed source clusters. Heuristic only, no actual route or feasibility/physical qualification.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));out=Path(r'D:\Data\电路实验\control162-cluster-demand206.json');assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for r in d['reports']:print(json.dumps(dict(seed=r['seed'],net_count=r['net_count'],wire_grid_length=r['bbox_wire_grid_length'],top=r['hotspots'][0])))
