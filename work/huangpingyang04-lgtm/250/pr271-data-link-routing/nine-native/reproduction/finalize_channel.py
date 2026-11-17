"""Attach the last two C ports directly to their own existing top conductors."""
from pathlib import Path
import csv,gzip,json,sys
root=Path(sys.argv[1]).resolve();case=root/'nine-channel'
sys.path.insert(0,str(root/'engine'))
from geometry import Occupancy,contains,too_close,segment_shape,via_shapes
from check import digest,verify
def load(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
spec=load(case/'spec.json');tech=spec['technology'];place=load(case/'placement.json')
landings=load(case/'landings.json');expected=load(case/'native-expected-contacts.json')
ox,oy=tech['origin'];step=tech['access_pitch'];routes={}
f=iter((case/'paths-final.txt').read_text().splitlines())
for line in f:
 i,nw,nv=map(int,line.split());n=spec['nets'][i];segments=[];vias=[]
 for _ in range(nw):
  x,y,a,b,l=map(int,next(f).split());segments.append({'a':[ox+x*step,oy+y*step],'b':[ox+a*step,oy+b*step],'layer':('M11','M12')[l]})
 for _ in range(nv):
  x,y=map(int,next(f).split());vias.append([ox+x*step,oy+y*step])
 routes[n['id']]={'segments':segments,'via11':vias,'via10':[{'pin':p,'at':landings[p]} for p in [n['driver'],*n['sinks']]]}
assert len(routes)==1049
upper=Occupancy(tech)
for name,r in routes.items():
 upper.add([segment_shape(s['layer'],s['a'],s['b'],tech) for s in r['segments']]+[s for p in r['via11'] for s in via_shapes('via11',p,tech)]+[s for v in r['via10'] for s in via_shapes('via10',v['at'],tech)],name)
owners={}
for r in csv.reader((root/'export-C/ports.tsv').open(),delimiter='\t'):
 if r[0]=='term':owners[r[1]]=r[4]
original=load(root/'nine/native-expected-contacts.json');skip={tuple(b) for p,b in original.items() if p.startswith('C0.')}
native=Occupancy(tech)
with gzip.open(root/'export-C/native.tsv.gz','rt') as f:
 for line in f:
  if line.startswith('#'):continue
  owner,layer,role,*raw=line.split();b=list(map(int,raw))
  if layer=='metal10' and tuple(b) not in skip:native.add([('M10',b)],owner)
for pin,b in expected.items():
 if pin.startswith('C0.'):native.add([('M10',b)],owners[pin.split('.',1)[1]])
def clear(owner,b):
 query=[b[0]-3000,b[1]-3000,b[2]+3000,b[3]+3000]
 return all(o==owner or not too_close(b,r,3000) for k in native.keys('M10',query) for o,r in native.occupants(k))
changes=[]
for i in (337,579):
 n=spec['nets'][i];pin=next(p for p in [n['driver'],*n['sinks']] if p.startswith('C0.'))
 r=routes[n['id']];owner=owners[pin.split('.',1)[1]];dx,dy=place['boxes_dbu']['C0'][:2];candidates=set()
 for s in r['segments']:
  if s['layer']!='M11':continue
  a,b=s['a'],s['b'];axis=0 if a[1]==b[1] else 1
  for v in range(min(a[axis],b[axis]),max(a[axis],b[axis])+1,400):
   p=a[:];p[axis]=v;candidates.add(tuple(p))
 for p in sorted(candidates,key=lambda p:abs(p[0]-landings[pin][0])+abs(p[1]-landings[pin][1])):
  b=[p[0]-dx-2000,p[1]-dy-2000,p[0]-dx+2000,p[1]-dy+2000]
  if not contains([0,0,5128000,2352000],b) or not clear(owner,b):continue
  if not upper.legal(via_shapes('via10',p,tech),n['id']):continue
  changes.append({'pin':pin,'from':landings[pin],'to':list(p)})
  landings[pin]=list(p);expected[pin]=b;spec['pins'][pin]=[[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]]
  for v in r['via10']:
   if v['pin']==pin:v['at']=list(p)
  native.add([('M10',b)],owner);upper.add(via_shapes('via10',p,tech),n['id']);break
 else:
  alternatives=[]
  for s in r['segments']:
   if s['layer']!='M12':continue
   a,b=s['a'],s['b'];axis=0 if a[1]==b[1] else 1
   for v in range(min(a[axis],b[axis]),max(a[axis],b[axis])+1,400):
    q=a[:];q[axis]=v
    if not (dx+2000<=q[0]<=dx+5126000 and dy+2000<=q[1]<=dy+2350000):continue
    for shift in (0,2000,-2000,4000,-4000,8000,-8000):
     p=q[:];p[1-axis]+=shift
     alternatives.append((abs(p[0]-landings[pin][0])+abs(p[1]-landings[pin][1]),p,q))
  for _,p,q in sorted(alternatives):
   b=[p[0]-dx-2000,p[1]-dy-2000,p[0]-dx+2000,p[1]-dy+2000]
   if not contains([0,0,5128000,2352000],b) or not clear(owner,b):continue
   if any(abs(q[0]-v[0])<8400 and abs(q[1]-v[1])<8400 for v in r['via11']):continue
   shapes=via_shapes('via10',p,tech)+via_shapes('via11',q,tech)
   if p!=q:shapes.append(segment_shape('M11',p,q,tech))
   if not upper.legal(shapes,n['id']):continue
   changes.append({'pin':pin,'from':landings[pin],'to':p,'new_v11':q})
   landings[pin]=p;expected[pin]=b;spec['pins'][pin]=[[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]]
   for v in r['via10']:
    if v['pin']==pin:v['at']=p
   r['via11'].append(q)
   if p!=q:r['segments'].append({'layer':'M11','a':p,'b':q})
   native.add([('M10',b)],owner);upper.add(shapes,n['id']);break
  else:raise ValueError(('No contact on existing conductor',pin))
result={'schema_version':'upper-router-result/1','spec_sha256':digest(spec),'context':spec['context'],'physical_qualified':False,'electrical_status':'not_evaluated','timing_status':'not_evaluated','status':'geometry_complete','routes':routes,'failed':{}}
out=root/'final';out.mkdir(exist_ok=True)
for name,value in [('spec',spec),('route',result),('placement',place),('native-expected-contacts',expected),('contact-corrections',changes),('lower-overlay',load(case/'lower-overlay.json'))]:write(out/(name+'.json'),value)
checks=verify(spec,result);write(out/'checks.json',checks)
rows=load(case/'branches.json')
with (out/'connections.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['net','group','driver','sink','status']);w.writeheader()
 for row in rows:w.writerow({**row,'status':'upper_geometry_checked'})
print(json.dumps({'contact_corrections':changes,'checks':checks}),flush=True)
