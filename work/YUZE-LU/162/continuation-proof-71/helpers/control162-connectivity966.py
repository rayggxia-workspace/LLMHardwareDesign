from pathlib import Path
import json,hashlib,time,numpy as np,scipy
from scipy.ndimage import label
h=Path(__file__).parent;parser=h/'control162-analyze941.py';code=parser.read_text(encoding='utf-8').split('target=meta',1)[0];exec(compile(code,str(parser),'exec'));started=time.monotonic();ordinary=set(names[locked:])
def analyze(mask):
 free=np.ones((3,ny,nx),dtype=bool);free[1]=False
 free[:,:4,:]=False;free[:,-4:,:]=False;free[:,:,:4]=False;free[:,:,-4:]=False
 owned={n:[]for n in ordinary}
 for v,n in mask.items():
  l=v//plane;y=(v%plane)//nx;x=v%nx;free[2*l,y,x]=False
  if n in ordinary:owned[n].append(v)
 via=np.zeros((ny,nx),dtype=bool);via[::2,::2]=True;via[1::2,1::2]=True
 assert not np.any(via[:,1:]&via[:,:-1])and not np.any(via[1:]&via[:-1])
 free[1]=free[0]&free[2]&via
 labels,components=label(free)
 sizes=np.bincount(labels[0].ravel(),minlength=components+1)+np.bincount(labels[2].ravel(),minlength=components+1)
 bad=[];specific={}
 for n in names[locked:]:
  points=owned[n];indices={v:i for i,v in enumerate(points)};parents=list(range(len(points)));first={};links=[set()for _ in points]
  def root(i):
   while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
   return i
  def union(i,j):parents[root(i)]=root(j)
  for i,v in enumerate(points):
   x,y,l=v%nx,(v%plane)//nx,v//plane
   for w in [v-1,v+1,v-nx,v+nx]+([(1-l)*plane+y*nx+x]if(x+y)%2==0 else[]):
    if w<0 or w>=2*plane:continue
    xx,yy,ll=w%nx,(w%plane)//nx,w//plane
    if not(4<=xx<nx-4 and 4<=yy<ny-4)or abs(x-xx)+abs(y-yy)+abs(l-ll)!=1:continue
    if w in indices:union(i,indices[w]);continue
    cid=int(labels[2*ll,yy,xx])
    if cid:
     links[i].add(cid)
     if cid in first:union(i,first[cid])
     else:first[cid]=i
  terminals=[indices[y*nx+x]for x,y in ends[n]];roots={root(i)for i in terminals}
  if len(roots)>1 or n=='net_9969':
   groups=[]
   for r in sorted(roots):
    group=[i for i in range(len(points))if root(i)==r];cs=set().union(*(links[i]for i in group))
    groups.append(dict(terminal_indices=[k for k,i in enumerate(terminals)if root(i)==r],own_fixed_nodes=len(group),free_components=sorted(cs),reachable_original_grid_vertices=len(group)+int(sum(sizes[c]for c in cs))))
   row=dict(net=n,connected=len(roots)==1,terminals=len(terminals),groups=groups)
   if len(roots)>1:bad.append(row)
   if n=='net_9969':specific=row
 return dict(shared_free_components=int(components),largest_free_component_vertices=int(max(sizes[1:],default=0)),checked_ordinary_nets=count-locked,disconnected_count=len(bad),disconnected=bad,target=specific)
before=analyze(fixed);after=analyze(restored)
assert not before['target']['connected']and after['target']['connected']
assert next(g['reachable_original_grid_vertices']for g in before['target']['groups']if 0 in g['terminal_indices'])==168
r=dict(passed=True,whole_system_qualified=False,route_qualified=False,seconds=time.monotonic()-started,before=before,after=after,source=meta,parser_sha256=hashlib.sha256(parser.read_bytes()).hexdigest(),numpy=np.__version__,scipy=scipy.__version__,scope='Static hard-connectivity diagnostic of one actual zero-native prefix. A 3-plane 6-neighbour labelling represents the original two grid layers and only checkerboard vias: middle via sites cannot touch horizontally or vertically. All foreign fixed M11 landings and actual frozen native vertices remain blocked. Per-net own fixed nodes/ports bridge shared free components with DSU; require all actual terminals connected, never require unused proxies connected. Net9969 independently reproduces the168-vertex goal component from direct full BFS944, and released-mask constructive A*941. Dynamic ordinary wire occupancy/cost/capacity competition is ignored; connected does not prove simultaneous routing or physical acceptance.')
(folder/'connectivity966.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(dict(passed=True,seconds=r['seconds'],before_disconnected=before['disconnected_count'],after_disconnected=after['disconnected_count'],after_bad=[x['net']for x in after['disconnected']],target_before=before['target'],target_after=after['target'])))
