from pathlib import Path
import json,hashlib,heapq,time,sys
h=Path(__file__).parent;folder=h/'control162-frozen-disconnection940';meta=json.loads((folder/'selected.json').read_text());began=time.monotonic()
for name,row in meta['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==row['sha256']
lines=(folder/'input.txt').read_text().splitlines();header=list(map(int,lines[0].split()));nx,ny,count,seed,rounds,weight,locked=header[:7];plane=nx*ny;names=[];ends={};limits={}
for line in lines[1:]:
 r=line.split();n=r[0];k=int(r[1]);names.append(n);ends[n]=[(int(r[2+2*i]),int(r[3+2*i]))for i in range(k)];limits[n]=int(r[-1])
assert len(names)==count
fixed={y*nx+x:n for n in names for x,y in ends[n]};assert len(fixed)==sum(map(len,ends.values()))
native={}
with(folder/'output.txt.native-prefix-paths.txt').open()as f:
 assert int(f.readline())==locked
 for _ in range(locked):
  n,k=f.readline().split();assert n==names[_]
  for i in range(int(k)):
   r=list(map(int,f.readline().split()));assert len(r)==1+3*r[0]
   for j in range(1,len(r),3):
    x,y,l=r[j:j+3];v=l*plane+y*nx+x;assert native.setdefault(v,n)==n;assert fixed.get(v,n)==n;fixed[v]=n
 assert not f.read().strip()
restored=fixed.copy();plan=json.loads((folder/'output.txt.pin-access.json').read_text());assert plan['assigned']==plan['terminals']==22302
for index,v,w in plan['plan']:
 n=names[index];assert index>=locked
 for node in ([w,w+plane]if v!=w else[w+plane]):assert fixed.get(node,n)==n;fixed[node]=n
target=meta['failure'].rsplit(': ',1)[1];assert target in ends and len(ends[target])==2
def search(mask,budget=65536):
 start=ends[target][1][1]*nx+ends[target][1][0];goal=ends[target][0][1]*nx+ends[target][0][0];gx,gy=ends[target][0]
 def allowed(v):return mask.get(v,target)==target
 def heuristic(v):return abs(v%nx-gx)+abs((v%plane)//nx-gy)
 q=[(8*heuristic(start),0,start)];dist={start:0};parent={};expanded=0
 while q:
  _,neg,v=heapq.heappop(q);cost=-neg
  if dist.get(v)!=cost:continue
  if v==goal:
   path=[v]
   while path[-1]!=start:path.append(parent[path[-1]])
   path.reverse()
   for a,z in zip(path,path[1:]):
    x,y,l=a%nx,(a%plane)//nx,a//plane;xx,yy,ll=z%nx,(z%plane)//nx,z//plane
    assert allowed(a)and allowed(z)and abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and(l==ll or(x+y)%2==0)
   return dict(found=True,expanded=expanded,visited=len(dist),path=path,wire_edges=sum(a//plane==z//plane for a,z in zip(path,path[1:])))
  if expanded==budget:return dict(found=False,expanded=expanded,visited=len(dist),reason='expansion-cap')
  expanded+=1;x,y,l=v%nx,(v%plane)//nx,v//plane
  for w,base in [(v-1,1 if l==0 else 2),(v+1,1 if l==0 else 2),(v-nx,1 if l==1 else 2),(v+nx,1 if l==1 else 2),((1-l)*plane+y*nx+x,3)]:
   if w<0 or w>=2*plane:continue
   xx,yy,ll=w%nx,(w%plane)//nx,w//plane
   if not(4<=xx<nx-4 and 4<=yy<ny-4)or abs(x-xx)+abs(y-yy)+abs(l-ll)!=1 or(l!=ll and(x+y)%2)or not allowed(w):continue
   alt=cost+base
   if alt<dist.get(w,10**30):dist[w]=alt;parent[w]=v;heapq.heappush(q,(alt+8*heuristic(w),-alt,w))
 return dict(found=False,expanded=expanded,visited=len(dist),reason='exhausted-component')
before=search(fixed);after=search(restored)
from collections import deque,Counter
start=ends[target][1][1]*nx+ends[target][1][0];goal=ends[target][0][1]*nx+ends[target][0][0]
queue=deque([start]);seen={start};blocked=Counter();found=False;cap=200000
while queue and len(seen)<cap:
 v=queue.popleft()
 if v==goal:found=True;break
 x,y,l=v%nx,(v%plane)//nx,v//plane
 for w in [v-1,v+1,v-nx,v+nx]+([(1-l)*plane+y*nx+x]if(x+y)%2==0 else[]):
  if w<0 or w>=2*plane:continue
  xx,yy,ll=w%nx,(w%plane)//nx,w//plane
  if not(4<=xx<nx-4 and 4<=yy<ny-4)or abs(x-xx)+abs(y-yy)+abs(l-ll)!=1:continue
  if fixed.get(w,target)!=target:blocked[fixed[w]]+=1;continue
  if w not in seen:seen.add(w);queue.append(w)
flood=dict(found=found,visited=len(seen),remaining=len(queue),capped=len(seen)>=cap,boundary_owners=blocked.most_common(24))
assert not found and not queue and len(seen)<cap,'Current full-search failure not independently proved by bounded flood'
before['independent_complete_component_flood']=flood
sys.path.insert(0,str(h/'LLMHardwareDesign-worktrees/issue-162-control/project/experiments/control_v1'));from router_conflict_snapshot import inspect
proof=inspect(folder/'output.txt.native-prefix-paths.txt',{n:ends[n]for n in names[:locked]},nx,ny,limits);assert proof['conflict_nodes']==0 and proof['all_trees_flood_verified']and proof['all_wire_budgets_verified']
result=dict(passed=True,whole_system_qualified=False,route_qualified=False,source=meta,target=target,retained_fixed_cells=len(fixed),restored_fixed_cells=len(restored),before=before,after=after,native_independent=proof,seconds=time.monotonic()-began,scope='One actual failed9060 prefix independently checks all1229native trees/zero-conflict/edges/vias/flood/originalwire. Bounded sparse A* on target pair compares all fixed temporary ordinary proxy reservations against releasing only these nonwire reservations; all24760actual M11 landings and every actual frozen native path retained. Dynamic ordinary usage is ignored in both, matching hard-connectivity question only. Found one path does not prove full routing or physical acceptance; capped search is inconclusive.')
(folder/'analysis942.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(dict(passed=True,target=target,before=before,after={k:v for k,v in after.items()if k!='path'},native_zero=proof['conflict_nodes']==0,seconds=result['seconds'])))
