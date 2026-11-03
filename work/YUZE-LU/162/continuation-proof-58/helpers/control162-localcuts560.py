from pathlib import Path
import json,subprocess,hashlib,time,collections
import numpy as np
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=home/'LLMHardwareDesign-deliveries/issue-162/local-cut-inputs-560';assert not out.exists();out.mkdir()
inp=r/'work/YUZE-LU/162/continuation-proof-58/r256-composition-453/upper-candidates/5400/route/router-input.txt';graph=out/'boundary-graph.json';remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/topology/boundary-graph.json';subprocess.run(['scp','yuzelu@10.129.166.172:'+remote,str(graph)],check=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(graph)=='49ba0e348f3583f6facdf60e771fe6f1329b46fe5aac872c3828d4b61ddb1a68'
raw=inp.read_text().splitlines();nx,ny,count=map(int,raw[0].split()[:3]);names=[];ends={};points=[];ids=[]
for i,line in enumerate(raw[1:]):
 a=line.split();n=int(a[1]);xy=[tuple(map(int,a[2+2*j:4+2*j]))for j in range(n)];names.append(a[0]);ends[a[0]]=xy;points+=xy;ids+=[i]*n
assert len(names)==count==11149 and len(set(points))==len(points);points=np.array(points);ids=np.array(ids);total=np.bincount(ids,minlength=count);xx,yy=points.T
rects={}
def add(x0,y0,x1,y1,label):
 x0,y0,x1,y1=max(4,int(x0)),max(4,int(y0)),min(nx-5,int(x1)),min(ny-5,int(y1))
 if x1>x0 and y1>y0:rects.setdefault((x0,y0,x1,y1),label)
g=json.loads(graph.read_text());groups=collections.defaultdict(list)
for bit,c in g['connections'].items():
 n='net_'+bit
 if n not in ends:continue
 es=[c['driver'],*c['sinks']];assert len(es)==len(ends[n])
 for e,p in zip(es,ends[n]):
  if e['instance']=='TOP':continue
  pin=e['pin'];base=pin.split('[')[0]
  if base.lower()in ['clk','rst_n','reset_n','vdd','vss']:continue
  groups[(e['instance'],base)].append(p);groups[(e['instance'],'ALL_SIGNAL_PINS')].append(p)
for key,ps in groups.items():
 if len(ps)<8:continue
 xs,ys=zip(*ps)
 for margin in [0,1,2,4,8,16,32]:add(min(xs)-margin,min(ys)-margin,max(xs)+margin,max(ys)+margin,'pin-bbox:'+str(key)+':margin'+str(margin))
for size in [8,16,32,64,128,256,512]:
 step=size//2;cells=set(zip((xx//step).tolist(),(yy//step).tolist()))
 for x,y in cells:
  for dx in [0,-1]:
   for dy in [0,-1]:add((x+dx)*step,(y+dy)*step,(x+dx)*step+size-1,(y+dy)*step+size-1,'sliding-size'+str(size))
rows=[];started=time.time()
for (x0,y0,x1,y1),label in rects.items():
 inside=(xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1);n=np.bincount(ids[inside],minlength=count);cross=(n>0)&(n<total);demand=int(cross.sum());w,h=x1-x0+1,y1-y0+1;capacity=2*(2*w+2*h-4)
 rows.append(dict(rect_grid=[x0,y0,x1,y1],label=label,inside_terminals=int(inside.sum()),crossing_distinct_nets=demand,two_layer_boundary_vertex_capacity=capacity,ratio=demand/capacity,violated=demand>capacity,crossing_net_examples=[names[i]for i in np.flatnonzero(cross)[:8]]))
worst=sorted(rows,key=lambda x:x['ratio'],reverse=True);result=dict(passed=True,whole_system_qualified=False,source_input=str(inp),source_input_sha256=sha(inp),actual_graph_remote=remote,actual_graph_sha256=sha(graph),script_sha256=sha(__file__),grid=[nx,ny],net_count=count,terminal_count=len(points),rectangles=len(rows),violations=sum(x['violated']for x in rows),worst=worst[:64],elapsed_seconds=time.time()-started,scope='Necessary local vertex cuts on actual current453/S5380 M11/M12 router input. Every net with an actual M11 terminal both inside and outside a grid rectangle must consume at least one distinct boundary vertex on either routing layer. For width,height>=2 the generous two-layer boundary capacity is2*(2w+2h-4); both layers allow both directions and every boundary vertex is counted available, no preferred-only substitution or obstacle capacity subtraction. A violated cut proves this exact two-layer grid routing scene cannot be vertex-disjoint, not arbitrary physical technologies or alternate landing models. Sampled zero violations is not routability/electrical/RC/timing qualification. Local NumPy metadata math only, no server login EDA or live-job changes.');(out/'receipt.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());(out/'all-cuts.json').write_bytes((json.dumps(rows)+'\n').encode());print(json.dumps(dict(rectangles=len(rows),violations=result['violations'],elapsed=result['elapsed_seconds'],worst=worst[:4])))
