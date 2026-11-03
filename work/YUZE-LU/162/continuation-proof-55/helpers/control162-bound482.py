import subprocess,shlex
q="""from pathlib import Path
import json,time,hashlib,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-rectilinear-ratio-bound-482';assert not out.exists();source=b/'source-474/project/experiments/control_v1/steiner_wire_bound.py';sys.path.insert(0,str(source.parent));from steiner_wire_bound import grid_tree_bound
rows=[]
for scene,seeds in [('r256-composition-359',[3733,4081,4160,4161,4250,4340,4390]),('r256-composition-453',[4661,4670,4760])]:
 for seed in seeds:
  p=b/scene/'upper-candidates'/str(seed)/'route/router-input.txt'
  if not p.exists():continue
  raw=p.read_bytes();lines=raw.decode().splitlines();header=list(map(int,lines[0].split()));locked=header[6];assert header[7]==1;rejected=[];strengthened=0
  for line in lines[1:locked+1]:
   fields=line.split();name=fields[0];n=int(fields[1]);v=list(map(int,fields[2:]));assert len(v)==n*2+1;points=list(zip(v[::2][:n],v[1::2][:n]));limit=v[-1];d=grid_tree_bound(points);strong=max(d['hpwl_grid_edges'],(2*d['metric_mst_grid_edges']+2)//3);strengthened+=strong>d['necessary_wire_grid_edges']
   if strong>limit:
    # Independent Kruskal verifies the MST used in every actual rejection.
    pts=sorted(set(points));edges=sorted((abs(x-xx)+abs(y-yy),i,j)for i,(x,y)in enumerate(pts)for j,(xx,yy)in enumerate(pts)if i<j);parent=list(range(len(pts)))
    def root(i):
     while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
     return i
    mst=0;used=0
    for cost,i,j in edges:
     a,c=root(i),root(j)
     if a!=c:parent[a]=c;mst+=cost;used+=1
     if used==len(pts)-1:break
    assert mst==d['metric_mst_grid_edges'];rejected.append(dict(net=name,terminals=n,wire_budget_grid_edges=limit,hpwl=d['hpwl_grid_edges'],metric_mst=mst,old_lower_bound=d['necessary_wire_grid_edges'],strong_lower_bound=strong,independent_kruskal_mst_verified=True))
  rows.append(dict(scene=scene,seed=seed,input=str(p),input_sha256=hashlib.sha256(raw).hexdigest(),priority_nets=locked,strictly_strengthened_nets=strengthened,rejected_count=len(rejected),rejected=rejected))
out.mkdir();d=dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),theorem_source='F.K. Hwang, On Steiner Minimal Trees with Rectilinear Distance, SIAM J.Appl.Math.30(1),104-114,1976, doi10.1137/0130013',theorem_url='https://epubs.siam.org/doi/abs/10.1137/0130013',method='max(HPWL,ceil(2*L1_metric_MST/3)) <= any rectilinear connected projected wire length; any two-layer grid routing has at least this total planar wire length, vias ignored. Compare exact actual router integer wire budgets. Independent Kruskal checks each rejecting Prim MST.',scope='Additional failure-only diagnosis; original nine final acceptance source files untouched. This rejects only these exact grid inputs/budgets when a bound exceeds budget; no all-placement or continuous-geometry impossibility claim, no route/RC/system qualification. Original searches/source/spec/output unchanged; no cancellation in this script.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps([dict(scene=r['scene'],seed=r['seed'],strengthened=r['strictly_strengthened_nets'],rejected=r['rejected_count'],examples=r['rejected'][:2])for r in rows]))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
