from pathlib import Path
import json,math,time,hashlib,collections
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
b=Path(r'D:\Data\电路实验');root=b/'control162-lp1664';out=b/'control162-milp1666';assert not out.exists();out.mkdir();p=json.loads((root/'placement.json').read_bytes());s=json.loads((root/'placement-search.json').read_bytes());e=s['electrical_refinement'];cl=e['clusters'];names=sorted(cl['dimensions']);ids={n:i for i,n in enumerate(names)};parents={n:ids[v['parent']]for n,v in cl['members'].items()};chosen=next(r for r in e['independent_trials']if r['seed']==e['selected_seed']);origins=np.array(chosen['coordinates'])+128;dims=np.array([cl['dimensions'][n]for n in names]);g=json.loads((b/'control162-snapshot1582/boundary-graph.json').read_bytes());lines=(root/'electrical-placement-input.txt').read_text().splitlines()[30:];netnames=['net_'+k for k in g['connections']]+['net_PG_VDD','net_PG_VSS'];assert len(lines)==len(netnames);nets=[];violations=[]
for name,line in zip(netnames,lines):
 a=line.split();budget=float(a[0]);external=int(a[1]);count=int(a[2]);coords=p['terminals'][name]
 if name.startswith('net_PG_'):assert budget==0;continue
 con=g['connections'][name[4:]];ends=[con['driver'],*con['sinks']];assert len(ends)==len(coords) and count==sum(e['instance']!='TOP'for e in ends)
 if budget<=0:continue
 row=[(None if v['instance']=='TOP' else parents[v['instance']],*xy)for v,xy in zip(ends,coords)];length=max(v[1]for v in row)-min(v[1]for v in row)+max(v[2]for v in row)-min(v[2]for v in row)
 if length*4>budget+1e-6:violations.append(dict(name=name,length_um=length*4,budget_um=budget))
 nets.append((name,row,budget/4))
assert len(violations)==4,violations
# Every movable variable is an INTEGER four-micron cluster translation.
# All original masks, relative members, die and external pins remain fixed.
var=59+4*len(nets);rr=[];cc=[];vv=[];ub=[]
def add(items,limit):
 idx=len(ub);ub.append(limit)
 for k,v in items:rr.append(idx);cc.append(k);vv.append(v)
for i in range(58):add([(i,1),(58,-1)],0);add([(i,-1),(58,-1)],0)
for i in range(29):
 for j in range(i):
  choices=[]
  for axis in range(2):
   if origins[i,axis]+dims[i,axis]<=origins[j,axis]+1e-7:choices.append((origins[j,axis]-origins[i,axis]-dims[i,axis],i,j,axis))
   if origins[j,axis]+dims[j,axis]<=origins[i,axis]+1e-7:choices.append((origins[i,axis]-origins[j,axis]-dims[j,axis],j,i,axis))
  assert choices,(names[i],names[j]);gap,a,z,axis=max(choices);add([(2*a+axis,1),(2*z+axis,-1)],gap/4)
for i,(name,ends,budget)in enumerate(nets):
 lo_x,hi_x,lo_y,hi_y=[59+4*i+j for j in range(4)]
 for parent,x,y in ends:
  for axis,v,l,h in [(0,x,lo_x,hi_x),(1,y,lo_y,hi_y)]:
   add([(l,1)]+([]if parent is None else[(2*parent+axis,-1)]),v)
   add([(h,-1)]+([]if parent is None else[(2*parent+axis,1)]),-v)
 add([(hi_x,1),(lo_x,-1),(hi_y,1),(lo_y,-1)],math.floor(budget+1e-8)-2)
lower=np.zeros(var);upper=np.full(var,np.inf);lower[:58]=-128;upper[:58]=128;upper[58]=128
for i in range(29):
 for axis,extent in [(0,p['width_um']),(1,p['height_um'])]:
  lower[2*i+axis]=max(-128,math.ceil((128-origins[i,axis])/4));upper[2*i+axis]=min(128,math.floor((extent-128-origins[i,axis]-dims[i,axis])/4))
c=np.zeros(var);c[58]=1;integrality=np.zeros(var);integrality[:58]=1
A=coo_matrix((vv,(rr,cc)),shape=(len(ub),var)).tocsc();started=time.time();res=milp(c,integrality=integrality,bounds=Bounds(lower,upper),constraints=LinearConstraint(A,np.full(len(ub),-np.inf),ub),options=dict(time_limit=30,mip_rel_gap=0));r=dict(status=int(res.status),message=res.message,execution_seconds=time.time()-started,variables=var,constraints=len(ub),baseline_violations=violations,whole_system_qualified=False,scope='Local bounded mathematical feasibility DIAGNOSTIC only, not accepted placement or physical result. Fixed16060die10676x10892 and29rigidclusters, externalpins fixed; integer4um shifts<=512um, original pairwise separation preserved; all10930measured necessary native/input budgets with additional8um HPWL margin. No producer, source, mask, gate or remote job change. Feasible solution needs actual sourcebound native-pin reconstruction and original3RC/geometry/P&R gates.')
if res.x is not None:
 x=res.x;assert np.max(A@x-np.array(ub))<1e-5 and max(abs(x[:58]-np.round(x[:58])))<1e-5
 shifts={n:[int(round(v))*4 for v in x[2*i:2*i+2]]for i,n in enumerate(names)};worst=[]
 for name,ends,budget in nets:
  coords=[(v[1]+(0 if v[0]is None else x[2*v[0]]),v[2]+(0 if v[0]is None else x[2*v[0]+1]))for v in ends];length=max(v[0]for v in coords)-min(v[0]for v in coords)+max(v[1]for v in coords)-min(v[1]for v in coords);assert length<=budget-2+1e-6;worst.append((budget-length)*4)
 r.update(feasible=True,max_shift_um=max(abs(v)for xy in shifts.values()for v in xy),shifts=shifts,minimum_necessary_hpwl_margin_um=min(worst),independent_all_actual_signal_hpwl_verified=True)
else:r['feasible']=False
(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
