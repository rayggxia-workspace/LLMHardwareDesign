import subprocess,shlex
q=r'''from pathlib import Path
import json,math,time,hashlib,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';out=b/'r256-local-rectangle-cut-387';assert not out.exists();g=json.loads((root/'topology/boundary-graph.json').read_text());m=json.loads((root/'selected/physical.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def crossing(nets,rect):
 x0,y0,x1,y1=rect;inside=lambda p:x0<=p[0]<=x1 and y0<=p[1]<=y1
 return[n for n,ends in nets.items()if any(inside(p)for p in ends)and not all(inside(p)for p in ends)]
def capacity(rect):
 x0,y0,x1,y1=rect;w=x1-x0+1;h=y1-y0+1;assert w>0 and h>0
 return 2*(w*h-max(0,w-2)*max(0,h-2))
assert capacity((0,0,2,2))==16 and capacity((0,0,0,0))==2
assert crossing({'a':[(1,1),(4,1)],'b':[(1,1),(2,1)],'c':[(7,7),(8,8)]},(0,0,2,2))==['a']
reports=[]
for seed in [3690,3691,3692,3693]:
 p=root/'cap-candidates'/str(seed)/'placement.json';data=json.loads(p.read_text());nets=data['terminals'];groups=collections.defaultdict(list)
 for bit,c in g['connections'].items():
  ends=[c['driver']]+c['sinks'];points=nets['net_'+bit];assert len(ends)==len(points)
  for end,point in zip(ends,points):
   n=end['instance']
   if n=='TOP':continue
   groups[n+'|all'].append(point);groups[n+'|'+end['pin'].split('[')[0]].append(point)
 rectangles={}
 for name,points in groups.items():
  if len(points)<8:continue
  xs=[p[0]for p in points];ys=[p[1]for p in points]
  for pad in [0,1,2,4,8]:
   rect=(min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad)
   if rect[0]<4 or rect[1]<4 or rect[2]>=data['width_um']/4-4 or rect[3]>=data['height_um']/4-4:continue
   rectangles.setdefault(rect,[]).append(name+':pad'+str(pad))
 rows=[]
 for rect,names in rectangles.items():
  hits=crossing(nets,rect);cap=capacity(rect);rows.append(dict(rect_grid=list(rect),groups=names,required_distinct_net_boundary_vertices=len(hits),maximum_two_layer_boundary_vertices=cap,necessary_ratio=len(hits)/cap,impossible=len(hits)>cap,example_nets=hits[:12]))
 rows.sort(key=lambda x:-x['necessary_ratio']);reports.append(dict(placement=str(p),placement_sha256=sha(p),rectangles_checked=len(rows),violated=sum(x['impossible']for x in rows),worst=rows[:30]))
out.mkdir();(out/'summary.json').write_text(json.dumps(dict(executed=True,whole_system_qualified=False,time=time.time(),inputs={str(root/'topology/boundary-graph.json'):sha(root/'topology/boundary-graph.json'),str(root/'selected/physical.json'):sha(root/'selected/physical.json')},placements=reports,scope='Failure-only exact distinct-net closed-rectangle vertex-cut necessary bound. Every net with an actual M11 terminal inside and outside must use at least one inside boundary vertex; both layers and all their boundary vertices are allowed, so capacity overestimates availability. Whole native pin array and every bus bounding rectangle with 0/1/2/4/8 grid padding sampled. Lack of a sampled violation does not prove routability or timing; no geometry or gate changes.'),indent=2));print(json.dumps([dict(placement=Path(r['placement']).parent.name,rectangles=r['rectangles_checked'],violated=r['violated'],worst=r['worst'][:1])for r in reports]))
'''
compile(q,'rect387','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
