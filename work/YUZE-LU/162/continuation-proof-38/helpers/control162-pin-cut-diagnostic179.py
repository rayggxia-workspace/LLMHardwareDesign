"""Read-only necessary vertex cuts around actual macro bounds and port edges."""
from pathlib import Path
import subprocess, shlex, json

q = r'''from pathlib import Path
import json,time,hashlib,math
c=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391')
m=json.loads((c/'selected/physical.json').read_text());g=json.loads((c/'topology/boundary-graph.json').read_text());rows=[]
for seed in [1580,1702]:
 path=c/'cap-capacity-candidates'/str(seed)/'placement.json';p=json.loads(path.read_text());nx=int(p['width_um']/4);ny=int(p['height_um']/4);rects={}
 for name,(x,y)in p['placements_um'].items():
  if name.startswith('link_'):continue
  w,h=m['leaves'][g['instances'][name]]['die_um'];x0,y0,x1,y1=math.floor(x/4),math.floor(y/4),math.ceil((x+w)/4),math.ceil((y+h)/4)
  for pad in [0,4,16,64]:rects[(max(4,x0-pad),max(4,y0-pad),min(nx-5,x1+pad),min(ny-5,y1+pad))]=name+':macro:'+str(pad)
  for size in [16,32,64,128]:
   for xx,yy in [(x0,(y0+y1)//2),(x1,(y0+y1)//2),((x0+x1)//2,y0),((x0+x1)//2,y1),(x0,y0),(x0,y1),(x1,y0),(x1,y1)]:
    rects[(max(4,xx-size//2),max(4,yy-size//2),min(nx-5,xx+size//2),min(ny-5,yy+size//2))]=name+':edge:'+str(size)
 worst=None;failures=[];tested=0
 for (x0,y0,x1,y1),label in rects.items():
  if x1<=x0 or y1<=y0:continue
  crossing=boundary_only=0
  for ends in p['terminals'].values():
   inside=outside=boundary=False
   for xx,yy in ends:
    if x0<=xx<=x1 and y0<=yy<=y1:
     inside=True
     if xx in (x0,x1)or yy in (y0,y1):boundary=True
    else:outside=True
   if inside and outside:crossing+=1
   elif boundary:boundary_only+=1
  cap=2*(2*(x1-x0+1)+2*(y1-y0+1)-4);demand=crossing+boundary_only;tested+=1
  row=dict(label=label,rect_grid=[x0,y0,x1,y1],crossing_distinct_nets=crossing,other_nets_with_fixed_boundary_terminals=boundary_only,optimistic_two_layer_boundary_vertices=cap,ratio=demand/cap)
  if worst is None or row['ratio']>worst['ratio']:worst=row
  if demand>cap:failures.append(row)
 rows.append(dict(seed=seed,placement_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source=str(path),tested_rectangles=tested,worst=worst,necessary_failures=failures))
print(json.dumps(dict(time=time.time(),reports=rows,whole_system_qualified=False,scope='Exact failure-only cut bound at actual native macro edges/corners, not only macro centers. Each crossing net and each other distinct net with a fixed boundary terminal needs a different boundary vertex; optimistically allow both layers and ignore all spacing/via/obstacle restrictions. Excess proves impossible fixed scene; no excess is NOT a routability proof. No placement, route, job or acceptance mutation.')))
'''
out=Path(r'D:\Data\电路实验\control162-pin-cut179.json')
assert not out.exists()
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45))
out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for r in d['reports']:print(json.dumps(r))
