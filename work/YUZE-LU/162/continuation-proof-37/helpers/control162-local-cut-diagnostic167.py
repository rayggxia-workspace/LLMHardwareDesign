"""Exact failure-only rectangular vertex cut bound on actual landing sites."""
import subprocess,shlex,json
from pathlib import Path
q=r'''from pathlib import Path
import json,time,hashlib
c=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391');manifest=json.loads((c/'selected/physical.json').read_text());graph=json.loads((c/'topology/boundary-graph.json').read_text());reports=[]
for seed in [1424,1580,1621,1622,1700,1702]:
 path=c/'cap-capacity-candidates'/str(seed)/'placement.json';p=json.loads(path.read_text());nx=int(p['width_um']/4);ny=int(p['height_um']/4);centers=[]
 for name,(x,y)in p['placements_um'].items():
  if name.startswith('link_'):continue
  w,h=manifest['leaves'][graph['instances'][name]]['die_um'];centers.append((name,round((x+w/2)/4),round((y+h/2)/4)))
 worst=None;failures=[];tested=0
 for name,x,y in centers:
  for size in [16,32,64,128,256]:
   x0=max(4,x-size//2);x1=min(nx-5,x+size//2);y0=max(4,y-size//2);y1=min(ny-5,y+size//2)
   if x1<=x0 or y1<=y0:continue
   demand=0
   for ends in p['terminals'].values():
    inside=False;outside=False
    for xx,yy in ends:
     if x0<=xx<=x1 and y0<=yy<=y1:inside=True
     else:outside=True
     if inside and outside:demand+=1;break
   capacity=2*(2*(x1-x0+1)+2*(y1-y0+1)-4);row=dict(center=name,rect_grid=[x0,y0,x1,y1],crossing_distinct_nets=demand,optimistic_two_layer_boundary_vertices=capacity,ratio=demand/capacity);tested+=1
   if worst is None or row['ratio']>worst['ratio']:worst=row
   if demand>capacity:failures.append(row)
 reports.append(dict(seed=seed,source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),tested_rectangles=tested,worst=worst,necessary_failures=failures))
print(json.dumps(dict(time=time.time(),reports=reports,whole_system_qualified=False,scope='Failure-only vertex cut: each distinct net with actual terminals inside and outside a closed grid rectangle consumes at least one boundary vertex. Capacity counts every boundary vertex on BOTH layers optimistically, ignoring all spacing/vias/obstacles. Excess proves no disjoint-grid route for that fixed scene; zero excess cannot prove routability. Native inputs and all actual acceptance gates unchanged.')))
'''
compile(q,'exact_rectangular_local_cut167','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out=Path(r'D:\Data\电路实验\control162-local-cut167.json');assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for r in d['reports']:print(json.dumps({k:r[k]for k in ['seed','tested_rectangles','worst','necessary_failures']}))
