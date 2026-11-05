import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,math,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-274';p=root/'native-pin-load307/native-pin-load.json';raw=p.read_bytes();data=json.loads(raw);rows=[];sources={str(p):hashlib.sha256(raw).hexdigest()}
for placement in data['placements']:
 folder=Path(placement['placement']);coord=folder/'placement.json';wire=folder/'wire-cap-lower-bound.json';a=json.loads(coord.read_text());w=json.loads(wire.read_text());terms=a['terminals'];sources[str(coord)]=hashlib.sha256(coord.read_bytes()).hexdigest();sources[str(wire)]=hashlib.sha256(wire.read_bytes()).hexdigest();wm={r['net']:r for r in w['rows']};extra=[]
 for r in placement['rows']:
  n=r['net'];pts=list(dict.fromkeys(tuple(x)for x in terms[n]));budget=wm[n]
  if len(pts)<3:continue
  # A metric MST cannot exceed twice any connected Steiner tree: double
  # that tree, visit terminals, shortcut in the L1 metric, then take MST.
  distances=[10**18]*len(pts);distances[0]=0;used=[False]*len(pts);mst=0
  for k in range(len(pts)):
   j=min((i for i in range(len(pts))if not used[i]),key=lambda i:distances[i]);used[j]=True;mst+=distances[j];x,y=pts[j]
   for i,(xx,yy)in enumerate(pts):
    if not used[i]:distances[i]=min(distances[i],abs(x-xx)+abs(y-yy))
  length=max(budget['minimum_wire_um'],4*math.ceil(mst/2));assert length+1e-7>=budget['minimum_wire_um']
  if length>budget['minimum_wire_um']+1e-7:
   caps={c:r['optimistic_total_with_minimum_pin_ff'][c]+budget['wire_capacitance_lower_bound_ff'][c]*(length/budget['minimum_wire_um']-1)for c in ['low','base','high']}
   extra.append(dict(net=n,driver=r['driver'],terminals=len(pts),original_hpwl_um=budget['minimum_wire_um'],metric_MST_grid_edges=mst,tree_wire_lower_bound_um=length,native_ground_cap_ff=r['native_ground_cap_ff'],minimum_input_pin_cap_ff=r['minimum_input_pin_cap_ff'],max_capacitance_ff=r['max_capacitance_ff'],lower_total_cap_ff=caps,violations={c:cap>r['max_capacitance_ff']+1e-9 for c,cap in caps.items()}))
 rows.append(dict(placement=str(folder),stronger_bounds=len(extra),violations={c:sum(r['violations'][c]for r in extra)for c in ['low','base','high']},rows=extra))
out=b/'r256-native-tree-cap-diagnostic-347';assert not out.exists();out.mkdir();result=dict(executed=True,whole_system_qualified=False,inputs=sources,placements=rows,scope='Failure-only necessary actual selected-terminal HPWL or L1 metric MST/2 lower bound, rounded up to4um grid, plus previously measured source-bound native ground and minimum actual input loads. Original uniform research RC model only. No route, geometry, PG or timing acceptance.');(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['placement'],'stronger',r['stronger_bounds'],'violations',r['violations'],'worst',sorted([dict(net=v['net'],driver=v['driver'],terminals=v['terminals'],ratio=max(v['lower_total_cap_ff'].values())/v['max_capacitance_ff'],wire=v['tree_wire_lower_bound_um'],hpwl=v['original_hpwl_um'])for v in r['rows']],key=lambda x:x['ratio'],reverse=True)[:3])
'''
compile(q,'treecap347','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
