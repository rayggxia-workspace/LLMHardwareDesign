"""Read-only coarse local wire-density diagnostic, never routability proof."""
import subprocess,shlex,json
from pathlib import Path
q=r'''from pathlib import Path
import json,hashlib,math,time
c=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391/cap-capacity-candidates');reports=[];bins=16
for seed in [1424,1580,1600,1601,1620,1621,1622]:
 p=c/str(seed)/'placement.json';d=json.loads(p.read_text());nx=d['width_um']/4;ny=d['height_um']/4;h=[[0.]*bins for _ in range(bins)];v=[[0.]*bins for _ in range(bins)];wire=0
 for name,ends in d['terminals'].items():
  xs=[r[0]for r in ends];ys=[r[1]for r in ends];x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);dx=x1-x0;dy=y1-y0;wire+=dx+dy
  if not dx and not dy:continue
  if not dx:x0-=.5;x1+=.5
  if not dy:y0-=.5;y1+=.5
  area=(x1-x0)*(y1-y0);xa=max(0,min(bins-1,int(x0*bins/nx)));xb=max(0,min(bins-1,int(x1*bins/nx)));ya=max(0,min(bins-1,int(y0*bins/ny)));yb=max(0,min(bins-1,int(y1*bins/ny)))
  for ix in range(xa,xb+1):
   xx=max(0,min(x1,(ix+1)*nx/bins)-max(x0,ix*nx/bins))
   for iy in range(ya,yb+1):
    yy=max(0,min(y1,(iy+1)*ny/bins)-max(y0,iy*ny/bins));fraction=xx*yy/area/(nx*ny/bins**2);h[ix][iy]+=dx*fraction;v[ix][iy]+=dy*fraction
 mean=sum(sum(r)for r in h+v)/(2*bins**2);assert math.isclose(mean,wire/(2*nx*ny),rel_tol=1e-10)
 top=sorted([(max(h[x][y],v[x][y]),x,y,h[x][y],v[x][y])for x in range(bins)for y in range(bins)],reverse=True)[:8]
 reports.append(dict(seed=seed,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),nets=len(d['terminals']),mean_two_layer_bbox_density=mean,peak_preferred_direction_density=top[0][0],bins_over_one=sum(max(h[x][y],v[x][y])>1 for x in range(bins)for y in range(bins)),top_bins=top,horizontal=h,vertical=v))
print(json.dumps(dict(time=time.time(),bins=bins,reports=reports,whole_system_qualified=False,scope='Search diagnostic: uniform bounding-box wire demand in coarse tiles, separate preferred directions; exact mass conservation. Does not prove feasibility, account for detours or qualify any physical result. Native masks and actual gates unchanged.')))
'''
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45))
out=Path(r'D:\Data\电路实验\control162-local-density164.json');assert not out.exists();out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
for d in data['reports']:print(json.dumps({k:d[k]for k in ['seed','nets','mean_two_layer_bbox_density','peak_preferred_direction_density','bins_over_one']}))
