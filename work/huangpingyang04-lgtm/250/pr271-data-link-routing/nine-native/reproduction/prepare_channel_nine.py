"""Nine-base packing with a clear interconnect channel and native port ingress."""
from copy import deepcopy
from collections import defaultdict
import csv,gzip,json
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root/'engine'))
from geometry import Occupancy,too_close,contains,segment_shape,via_shapes
def load(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
base=root.parent/'hpy-four-compact.uwoxpDJq/compact'
spec=load(base/'check/spec.json');old=load(base/'check/route.json')['routes'];oldplace=load(base/'placement.json')
tech=spec['technology'];delta=[3064000,2432000]
def box(x,y,w,h):return [round(v*2000) for v in (x,y,x+w,y+h)]
boxes={k:deepcopy(v) for k,v in oldplace['boxes_dbu'].items() if k in ('P0','P1')}
boxes.update(C0=box(1532,3500.8,2564,1176),U0=box(4207.2,3564.8,2400,1600),
 P2=box(3016,32,1686,2245),U1=box(4750,32,2400,1600),F0=box(5144,1680,1096,1126),
 J0=box(0,2320,2088,1128),J1=box(2120,2320,2088,1128))
for a in boxes:
 for b in boxes:
  if a<b:assert not too_close(boxes[a],boxes[b],0),(a,b)
bounds=[0,0,max(b[2] for b in boxes.values())+64000,max(b[3] for b in boxes.values())+64000]
tech['bounds']=bounds
spec['context']={'laser_in_layer_bends':True,'compute_blocks':sorted(boxes),'standalone_readers':False,'native_contacts_readback':'pending'}
def shift(r,d):
 r=deepcopy(r)
 for s in r['segments']:
  for p in (s['a'],s['b']):p[0]+=d[0];p[1]+=d[1]
 for p in r['via11']:p[0]+=d[0];p[1]+=d[1]
 for v in r['via10']:v['at'][0]+=d[0];v['at'][1]+=d[1]
 return r
traces={k:shift(v,delta) if any(p['pin'].startswith('C0.') for p in v['via10']) else deepcopy(v) for k,v in old.items()}
for axis in (0,1):
 bounds[axis+2]=max(bounds[axis+2],max(p[axis] for r in traces.values() for s in r['segments'] for p in (s['a'],s['b']))+64000)
upper=Occupancy(tech)
for name,r in traces.items():
 shapes=[segment_shape(s['layer'],s['a'],s['b'],tech) for s in r['segments']]
 shapes += [sh for p in r['via11'] for sh in via_shapes('via11',p,tech)]
 shapes += [sh for v in r['via10'] for sh in via_shapes('via10',v['at'],tech)]
 for shape in shapes:assert upper.legal([shape],name),(name,shape)
 upper.add(shapes,name)
pin_net={p:n['id'] for n in spec['nets'] for p in [n['driver'],*n['sinks']]}
native=Occupancy(tech);owners={}
expected=load(root/'nine/native-expected-contacts.json')
skip={tuple(b) for p,b in expected.items() if p.startswith('C0.')}
for r in csv.reader((root/'export-C/ports.tsv').open(),delimiter='\t'):
 if r[0]=='term':owners[r[1]]=r[4]
with gzip.open(root/'export-C/native.tsv.gz','rt') as f:
 for line in f:
  if line.startswith('#'):continue
  owner,layer,role,*raw=line.split();b=list(map(int,raw))
  if layer=='metal10' and tuple(b) not in skip:native.add([('M10',b)],owner)
def native_clear(owner,b):
 lookup=[b[0]-3000,b[1]-3000,b[2]+3000,b[3]+3000]
 return all(o==owner or not too_close(b,r,3000) for k in native.keys('M10',lookup) for o,r in native.occupants(k))
def global_box(b,origin):return [b[0]+origin[0],b[1]+origin[1],b[2]+origin[0],b[3]+origin[1]]
def center(b):return [(b[0]+b[2])//2,(b[1]+b[3])//2]
def rename(p):return p.replace('C0_projection_reader.peer_','C0.projection_s_').replace('P2_down_reader.peer_','P2.down_s_')
spec['pins']={p:[[v+(delta[i%2] if p.startswith(('C0.','U0.')) else 0) for i,v in enumerate(b)] for b in rs]
              for p,rs in spec['pins'].items() if '_reader.' not in p}
landings={v['pin']:v['at'] for r in traces.values() for v in r['via10'] if '_reader.' not in v['pin']}
helpers=[];fixed_c={};moved=0
offsets=[(x*3200,y*3200) for x in range(-80,81) for y in range(-30,31)]
for pin,before in expected.items():
 if not pin.startswith('C0.') or pin.startswith('C0.projection_s_'):continue
 net=pin_net[pin];name=pin.split('.',1)[1];owner=owners[name];origin=boxes['C0'][:2]
 own=[segment_shape(s['layer'],s['a'],s['b'],tech)[1] for s in traces[net]['segments'] if s['layer']=='M11']
 def preference(d):
  b=[before[0]+d[0],before[1]+d[1],before[2]+d[0],before[3]+d[1]];g=global_box(b,origin)
  return (not any(contains(r,g) for r in own),abs(d[0])+abs(d[1]),abs(d[1]),d)
 for dx,dy in sorted(offsets,key=preference):
  b=[before[0]+dx,before[1]+dy,before[2]+dx,before[3]+dy]
  g=global_box(b,origin);p=center(g)
  if not contains([0,0,5128000,2352000],b) or not native_clear(owner,b):continue
  if not upper.legal(via_shapes('via10',p,tech),net):continue
  fixed_c[pin]=b;spec['pins'][pin]=[g]
  oldp=landings[pin];landings[pin]=p
  if not any(contains(r,g) for r in own):helpers.append({'net':net,'a':oldp,'b':p,'kind':'C-native-contact'})
  for v in traces[net]['via10']:
   if v['pin']==pin:v['at']=p
  native.add([('M10',b)],owner);upper.add(via_shapes('via10',p,tech),net)
  moved+=bool(dx or dy)
  break
 else:raise ValueError(('No source-bound C contact',pin))

projection=[]
for i,n in enumerate(spec['nets']):
 if not n['id'].startswith('s128-'):continue
 r=traces[n['id']];virtual=next(v for v in r['via10'] if '_reader.' in v['pin'])
 oldname=virtual['pin'];pin=rename(oldname);p=virtual['at']
 n['driver']=rename(n['driver']);n['sinks']=[rename(x) for x in n['sinks']]
 if pin.startswith('P2.down_s_'):
  # The former free endpoint is now a native port in P2's expanded west collar.
  spec['pins'][pin]=[[p[0]-2000,p[1]-2000,p[0]+2000,p[1]+2000]]
  landings[pin]=p;virtual['pin']=pin
 else:projection.append((p[1],p[0],i,pin,p[:]))

for rank,(_,_,i,pin,virtual) in enumerate(sorted(projection)):
 n=spec['nets'][i];r=traces[n['id']]
 local=box(7.095,179.07+4.8*rank,2,2)
 assert native_clear('new-projection',local),(pin,local)
 native.add([('M10',local)],'new-projection-'+str(rank))
 target=center(global_box(local,boxes['C0'][:2]));spec['pins'][pin]=[global_box(local,boxes['C0'][:2])];landings[pin]=target
 anchor=[round((5200.095+4.8*rank)*2000),round((160.07+4.8*rank)*2000)]
 hy=round((1500.07+4.8*rank)*2000);dx=round((400.095+4.8*rank)*2000)
 path=[anchor,[anchor[0],hy],[dx,hy],[dx,target[1]],target]
 for k,(a,b) in enumerate(zip(path,path[1:])):r['segments'].append({'a':a,'b':b,'layer':'M12' if k%2==0 else 'M11'})
 r['via11'].extend(path[:-1])
 for v in r['via10']:
  if '_reader.' in v['pin']:v['pin']=pin;v['at']=target
 helpers.append({'net':n['id'],'a':virtual,'b':anchor,'kind':'projection-channel-entry'})

# All frozen paths and the dedicated channel must be mutually legal before search.
check_occ=Occupancy(tech)
for n in spec['nets']:
 for p in [n['driver'],*n['sinks']]:
  sh=via_shapes('via10',landings[p],tech)
  assert check_occ.legal(sh,n['id']),(p,'native access')
  check_occ.add(sh,n['id'])
for n in spec['nets']:
 r=traces[n['id']]
 for shape in [segment_shape(s['layer'],s['a'],s['b'],tech) for s in r['segments']]+[sh for p in r['via11'] for sh in via_shapes('via11',p,tech)]:
  assert check_occ.legal([shape],n['id']),(n['id'],shape)
  check_occ.add([shape],n['id'])

out=root/'nine-channel';out.mkdir()
place={'units_per_um':2000,'variant':'nine-native-channel','compute_blocks':sorted(boxes),'boxes_dbu':boxes,'bounds_dbu':bounds,
       'standalone_reader_blocks':[],'peripheral_blocks':[],'native_origin_dbu':{k:boxes[k][:2] for k in ('C0','P2')},
       'P2_original_body_shift_dbu':[432000,0],'original_placement':oldplace,'attention_motion_from_compact_dbu':delta}
write(out/'spec.json',spec);write(out/'placement.json',place);write(out/'landings.json',landings);write(out/'helpers.json',helpers)
write(out/'frozen.json',traces)
rows=[]
with (base/'check/connections.csv').open() as f:
 for row in csv.DictReader(f):rows.append({k:rename(v) if k in ('driver','sink') else v for k,v in row.items() if k!='status'})
write(out/'branches.json',rows)
expected={}
for pin,rects in spec['pins'].items():
 block,name=pin.split('.',1)
 if block not in ('C0','P2'):continue
 (b,)=rects;dx,dy=boxes[block][:2];expected[pin]=[b[0]-dx,b[1]-dy,b[2]-dx,b[3]-dy]
write(out/'native-expected-contacts.json',expected)
lower=load(base/'lower-overlay.json')['by_terminal']
lower={k:v for k,v in lower.items() if k.split('.')[0] in ('P0','P1','U0')}
for pin,shapes in lower.items():
 if pin.startswith('U0.'):lower[pin]=[[l,[v+delta[i%2] for i,v in enumerate(b)]] for l,b in shapes]
write(out/'lower-overlay.json',{'by_terminal':lower})
ox,oy=tech['origin'];step=tech['access_pitch']
def point(p):
 assert (p[0]-ox)%step==0 and (p[1]-oy)%step==0,p
 return (p[0]-ox)//step,(p[1]-oy)//step
with (out/'nets.txt').open('w') as f:
 print(5,5,(bounds[2]-ox-2000)//step,(bounds[3]-oy-2000)//step,len(spec['nets']),file=f)
 for i,n in enumerate(spec['nets']):
  pins=[n['driver'],*n['sinks']];print(i,len(pins),0,file=f)
  for p in pins:print(*point(landings[p]),file=f)
with (out/'frozen.txt').open('w') as f:
 for i,n in enumerate(spec['nets']):
  r=traces[n['id']];print(i,len(r['segments']),len(r['via11']),file=f)
  for s in r['segments']:print(*point(s['a']),*point(s['b']),int(s['layer']=='M12'),file=f)
  for p in r['via11']:print(*point(p),file=f)
indices={n['id']:i for i,n in enumerate(spec['nets'])}
with (out/'helpers.txt').open('w') as f:
 for h in helpers:print(indices[h['net']],*point(h['a']),*point(h['b']),file=f)
print('Nine native blocks, frozen channel geometry clean; C contacts moved',moved,'local gaps',len(helpers),flush=True)
