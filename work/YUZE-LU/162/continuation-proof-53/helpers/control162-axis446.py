import subprocess,shlex
q="""from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-full-axis-cut-446';assert not out.exists();rows=[]
for seed in [3690,4240]:
 task=4340 if seed==4240 else 4081;p=b/'r256-composition-359/upper-candidates'/str(task)/'route/router-input.txt';raw=p.read_bytes();lines=raw.decode().splitlines();header=list(map(int,lines[0].split()));nx,ny,count=header[:3];dx=[0]*nx;dy=[0]*ny;hpwl=0
 for line in lines[1:]:
  parts=line.split();n=int(parts[1]);xy=list(map(int,parts[2:2+2*n]));xs=xy[::2];ys=xy[1::2];xl,xh=min(xs),max(xs);yl,yh=min(ys),max(ys);dx[xl]+=1;dx[xh]-=1;dy[yl]+=1;dy[yh]-=1;hpwl+=xh-xl+yh-yl
 assert len(lines)-1==count
 def scan(d,start,end,capacity):
  running=0;maxd=0;worst=None
  for i,value in enumerate(d):
   running+=value
   if start<=i<end and running>maxd:maxd=running;worst=i
  return dict(maximum_net_crossings=maxd,cut_coordinate=worst,two_layer_edge_capacity=capacity,necessary_ratio=maxd/capacity,violated=maxd>capacity)
 rows.append(dict(placement=seed,router_input=str(p),router_input_sha256=hashlib.sha256(raw).hexdigest(),nx=nx,ny=ny,nets=count,minimum_hpwl_wire_edges=hpwl,available_vertices=2*(nx-8)*(ny-8),x_cut=scan(dx,4,nx-5,2*(ny-8)),y_cut=scan(dy,4,ny-5,2*(nx-8))))
out.mkdir();d=dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Complete full-axis edge cuts for actual router input, every net spanning a cut requires at least one edge crossing. Both layers can route both directions, so actual capacity upper bound uses both layers. No single-direction preferred-layer limit substituted. These cuts are only necessary bounds, no cut violation is no routing or electrical feasibility proof. Light metadata/math only; no EDA on login host.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps(rows))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
