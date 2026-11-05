from pathlib import Path
from collections import deque,Counter
import json,hashlib,time
h=Path(__file__).parent;root=h/'control162-pin-matching840';assert not root.exists();root.mkdir();started=time.time();inp=h/'control162-static795/input.txt';raw=inp.read_bytes();lines=raw.decode().splitlines();nx,ny,count,seed,rounds,weight,locked,*_=map(int,lines[0].split());pins=[];owners={}
for n,line in enumerate(lines[1:]):
 p=line.split();k=int(p[1])
 for j in range(k):
  x,y=map(int,p[2+2*j:4+2*j]);assert (x,y)not in owners;owners[x,y]=n;pins.append(dict(net=n,name=p[0],terminal=j,x=x,y=y))
even={(p['x'],p['y']):p['net']for p in pins if(p['x']+p['y'])%2==0};assign={};left=[];adj=[];resources=[];resource_id={};zero=[]
for i,p in enumerate(pins):
 x,y,n=p['x'],p['y'],p['net']
 if(x+y)%2==0:assign[i]=(x,y);continue
 candidates=[q for q in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]if 4<=q[0]<nx-4 and 4<=q[1]<ny-4 and owners.get(q,n)==n]
 aliases=[q for q in candidates if even.get(q)==n]
 if aliases:assign[i]=aliases[0];continue
 options=[]
 for q in candidates:
  assert q not in even
  if q not in resource_id:resource_id[q]=len(resources);resources.append(q)
  options.append(resource_id[q])
 if not options:zero.append(i)
 left.append(i);adj.append(options)
match_l=[-1]*len(left);match_r=[-1]*len(resources);matched=0
while True:
 dist=[-1]*len(left);queue=deque()
 for a in range(len(left)):
  if match_l[a]<0:dist[a]=0;queue.append(a)
 while queue:
  a=queue.popleft()
  for b in adj[a]:
   aa=match_r[b]
   if aa>=0 and dist[aa]<0:dist[aa]=dist[a]+1;queue.append(aa)
 def augment(a):
  for b in adj[a]:
   aa=match_r[b]
   if aa<0 or(dist[aa]==dist[a]+1 and augment(aa)):
    match_l[a]=b;match_r[b]=a;return True
  dist[a]=-1;return False
 added=sum(augment(a)for a in range(len(left))if match_l[a]<0)
 if not added:break
 matched+=added
for a,b in enumerate(match_l):
 if b>=0:assign[left[a]]=resources[b]
shared=0
for a,b in enumerate(match_l):
 if b>=0:continue
 i=left[a];n=pins[i]['net']
 for bb in adj[a]:
  aa=match_r[bb]
  if aa>=0 and pins[left[aa]]['net']==n:assign[i]=resources[bb];shared+=1;break
proxy_owners={};m11=dict(owners)
for i,q in assign.items():
 p=pins[i];n=p['net'];assert(q[0]+q[1])%2==0 and abs(p['x']-q[0])+abs(p['y']-q[1])<=1
 assert m11.get(q,n)==n and proxy_owners.get(q,n)==n;m11[q]=proxy_owners[q]=n
unresolved=[pins[i]for i in range(len(pins))if i not in assign]
plans=[dict(pin=pins[i],proxy=list(q))for i,q in sorted(assign.items())];planraw=(json.dumps(plans,ensure_ascii=False,indent=2)+'\n').encode();(root/'static-plan.json').write_bytes(planraw)
r=dict(passed=True,whole_system_qualified=False,scope='Local static matching of at-most-one-edge M11 escapes to even M12 proxies for all actual terminals. Direct even proxies and same-net even aliases allowed; other odd endpoints matched uniquely, with optional same-net post-match sharing. Every assigned M11 stub and M12 proxy independently owner/parity/bounds checked. Ignores all routed wires, congestion/history, native finite-wire feasibility and fullscene routing/timing; not a production plan or physical acceptance.',input_sha256=hashlib.sha256(raw).hexdigest(),program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),terminal_count=len(pins),even_direct=len(even),odd_left=len(left),unique_matching=matched,same_net_post_aliases=shared,assigned=len(assign),unresolved=unresolved,zero_candidate_terms=[pins[i]for i in zero],distinct_proxies=len(proxy_owners),plan_sha256=hashlib.sha256(planraw).hexdigest(),elapsed_seconds=time.time()-started)
(root/'receipt.json').write_bytes((json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in r.items()if k not in ['unresolved','zero_candidate_terms']}));print('unresolved',len(unresolved),'zero_candidates',len(zero))
