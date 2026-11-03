import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,collections,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-composition-274/upper-candidates/2670/route/router-input.txt';raw=p.read_bytes();lines=raw.decode().splitlines();nx,ny,count=map(int,lines[0].split()[:3]);nets={}
for line in lines[1:]:
 f=line.split();k=int(f[1]);nets[f[0]]=[tuple(map(int,f[2+2*i:4+2*i]))for i in range(k)]
axis=[]
for dim,n,other in [(0,nx,ny),(1,ny,nx)]:
 delta=[0]*(n+1)
 for pts in nets.values():
  lo=min(p[dim]for p in pts);hi=max(p[dim]for p in pts)
  if lo<hi:delta[lo]+=1;delta[hi]-=1
 demand=0;rows=[]
 for i in range(4,n-5):demand+=delta[i];rows.append((demand,i))
 peak,at=max(rows);axis.append(dict(axis='x'if dim==0 else'y',peak_crossing_nets=peak,cut_at=at,loose_edge_capacity=2*(other-8),proven_impossible=peak>2*(other-8)))
out=b/'r256-grid-cut-diagnostic-339';assert not out.exists();out.mkdir();r=dict(whole_system_qualified=False,inputs={str(p):hashlib.sha256(raw).hexdigest()},axis_cuts=axis,scope='Necessary edge-disjoint cut lower bounds on actual two-layer allowed4-neighbor grid, not route or physical acceptance. No inference of sufficiency.');(out/'summary.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
for s in ['r256-complete-path-preflight-337','r256-complete-path-full-337']:
 p=b/s/'receipt.json';print(s,json.loads(p.read_text())if p.exists()else'pending')
'''
compile(q,'cut339','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
