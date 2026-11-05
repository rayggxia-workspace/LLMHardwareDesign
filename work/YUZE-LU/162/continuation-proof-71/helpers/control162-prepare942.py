from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-analyze941.py').read_text(encoding='utf-8').replace('analysis941.json','analysis942.json')
needle='before=search(fixed);after=search(restored)'
addition='''before=search(fixed);after=search(restored)
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
before['independent_complete_component_flood']=flood'''
assert s.count(needle)==1;s=s.replace(needle,addition);s=s.replace("before=before,after=", "before=before,after=")
compile(s,'analyze942','exec');(h/'control162-analyze942.py').write_bytes(s.encode())
