from pathlib import Path
import json,hashlib,collections,heapq,random,time,sys
home=Path(__file__).parent;out=home/'control162-native-repair897';d=json.loads((out/'diagnostic.json').read_text());assert hashlib.sha256((out/'native-paths.txt').read_bytes()).hexdigest()==d['snapshot_sha256'];assert hashlib.sha256((out/'input.txt').read_bytes()).hexdigest()==d['original_input_sha256'];assert d['native_log_filtered_byte_exact']and d['main_failure_log_byte_exact'];began=time.monotonic()
with(out/'input.txt').open()as f:
 header=list(map(int,f.readline().split()));nx,ny,count,seed,rounds,weight,locked=header[:7];nets={};limits={}
 for line in f:
  row=line.split();k=int(row[1]);nets[row[0]]=[(int(row[2+2*i]),int(row[3+2*i]))for i in range(k)];limits[row[0]]=int(row[-1])
plane=nx*ny;pin_owner={y*nx+x:n for n,ends in nets.items()for x,y in ends};assert len(pin_owner)==24760
paths={};points={};usage=collections.Counter()
with(out/'native-paths.txt').open()as f:
 assert int(f.readline())==locked
 for name in list(nets)[:locked]:
  n,k=f.readline().split();assert name==n;paths[n]=[];points[n]=set()
  for i in range(int(k)):
   row=list(map(int,f.readline().split()));path=[row[j+2]*plane+row[j+1]*nx+row[j]for j in range(1,len(row),3)];paths[n].append(path);points[n].update(path)
  usage.update(points[n])
focus=sorted({n for cell in d['conflict_cells']for n in cell['nets']});assert len(focus)==18 and all(len(nets[n])==2 for n in focus)

def search(n,current,budget=16384):
 target=nets[n][0][1]*nx+nets[n][0][0];start=nets[n][1][1]*nx+nets[n][1][0]
 def allowed(v):return not current[v]and(v>=plane or pin_owner.get(v,n)==n)
 if not allowed(start)or not allowed(target):return None,dict(expanded=0,reason='occupied-endpoint')
 tx,ty=nets[n][0];h=lambda v:abs(v%nx-tx)+abs((v%plane)//nx-ty)
 q=[(8*h(start),0,start)];distance={start:0};parent={};expanded=0
 while q:
  _,negative,v=heapq.heappop(q);cost=-negative
  if distance.get(v)!=cost:continue
  if v==target:
   path=[v]
   while path[-1]!=start:path.append(parent[path[-1]])
   path.reverse();wires=sum(a//plane==z//plane for a,z in zip(path,path[1:]));assert len(path)==len(set(path))
   if wires>limits[n]:return None,dict(expanded=expanded,reason='over-wire',wire=wires,limit=limits[n])
   for a,z in zip(path,path[1:]):
    x,y,l=a%nx,(a%plane)//nx,a//plane;xx,yy,ll=z%nx,(z%plane)//nx,z//plane
    assert abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and (l==ll or(x+y)%2==0)and allowed(z)
   return path,dict(expanded=expanded,reason='found',wire=wires,limit=limits[n])
  if expanded==budget:return None,dict(expanded=expanded,reason='expansion-cap')
  expanded+=1;x,y,l=v%nx,(v%plane)//nx,v//plane
  for w,base in [(v-1,1 if l==0 else 2),(v+1,1 if l==0 else 2),(v-nx,1 if l==1 else 2),(v+nx,1 if l==1 else 2),((1-l)*plane+y*nx+x,3)]:
   if w<0 or w>=2*plane:continue
   xx,yy,ll=w%nx,(w%plane)//nx,w//plane
   if not(4<=xx<nx-4 and 4<=yy<ny-4)or abs(x-xx)+abs(y-yy)+abs(l-ll)!=1 or (l!=ll and(x+y)%2)or not allowed(w):continue
   alt=cost+base
   if alt<distance.get(w,10**30):distance[w]=alt;parent[w]=v;heapq.heappush(q,(alt+8*h(w),-alt,w))
 return None,dict(expanded=expanded,reason='exhausted')

single=[]
for n in focus:
 for v in points[n]:usage[v]-=1
 path,r=search(n,usage)
 for v in points[n]:usage[v]+=1
 single.append(dict(net=n,**r))
print(json.dumps(dict(single_found=sum(x['reason']=='found'for x in single),single_cases=len(single),seconds=time.monotonic()-began)),flush=True)
base=usage.copy()
for n in focus:
 for v in points[n]:base[v]-=1
assert max(base.values())==1
orders=[focus,list(reversed(focus))];r=random.Random(897);order=focus.copy();r.shuffle(order);orders.append(order)
batches=[];winner=None
for i,order in enumerate(orders):
 current=base.copy();replacement={};rows=[]
 for n in order:
  path,proof=search(n,current);rows.append(dict(net=n,**proof))
  if path is None:break
  replacement[n]=path;current.update(set(path))
 ok=len(replacement)==len(focus);batches.append(dict(attempt=i,complete=ok,rows=rows));print(json.dumps(dict(batch=i,complete=ok,routed=len(replacement),seconds=time.monotonic()-began)),flush=True)
 if ok:winner=replacement;break
receipt=dict(passed=True,whole_system_qualified=False,route_qualified=False,scope='Bounded independent Python A*8 analysis of one actual native-only failed snapshot. Preserve all11149 landing owners and other native paths. Single-net free candidates and simultaneous removal of18 conflict-involved trees are comparisons only. Found paths independently check edges/vias/remaining original wire budget; empty/capped search is inconclusive. No fullscene or physical acceptance.',case=10,source_snapshot_sha256=d['snapshot_sha256'],input_sha256=d['original_input_sha256'],single=single,batches=batches,all_dirty_batch_found=winner is not None,seconds=time.monotonic()-began)
if winner:
 final=out/'native-batch-candidate.txt'
 with final.open('w')as f:
  f.write(str(locked)+'\n')
  for n in list(nets)[:locked]:
   ps=[[nets[n][0][1]*nx+nets[n][0][0]],winner[n]]if n in winner else paths[n];f.write(n+' '+str(len(ps))+'\n')
   for path in ps:f.write(str(len(path))+' '+' '.join(str(k)for v in path for k in(v%nx,(v%plane)//nx,v//plane))+'\n')
 sys.path.insert(0,str(home/'LLMHardwareDesign-worktrees/issue-162-control/project/experiments/control_v1'));from router_conflict_snapshot import inspect
 proof=inspect(final,{n:nets[n]for n in list(nets)[:locked]},nx,ny,limits);assert proof['conflict_nodes']==0 and proof['all_trees_flood_verified']and proof['all_wire_budgets_verified'];receipt['independent_native_candidate']=proof;receipt['candidate_sha256']=hashlib.sha256(final.read_bytes()).hexdigest()
 blocked=0
 for n in list(nets)[locked:]:
  for x,y in nets[n]:
   v=y*nx+x;neighbours=[v-1,v+1,v-nx,v+nx]+([v+plane]if(x+y)%2==0 else[])
   if not any(not current[w]and(w>=plane or pin_owner.get(w,n)==n)for w in neighbours):blocked+=1
 receipt['ordinary_terminals_without_free_first_exit_after_native_candidate']=blocked
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(passed=True,all_dirty_batch_found=winner is not None,seconds=time.monotonic()-began)))
