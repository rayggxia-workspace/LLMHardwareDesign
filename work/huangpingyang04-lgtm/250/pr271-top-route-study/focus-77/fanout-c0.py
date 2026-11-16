"""Fan out the sole missing M11 entrance using C0's verified lower-metal overlay."""
from pathlib import Path
import csv
import runpy
import sys

import lower_rules as geo


mode,plan_dir,output=sys.argv[1:]; plan_dir,output=map(Path,(plan_dir,output))
root=Path.cwd()
data=root/'precheck-final'
old_root=root.parent/'hpy-pr276-clean1184.kFNrCO4l'
old=old_root/'fanout-C0-retry'
helpers=runpy.run_path(str(root/'refresh-fanout.py'))
placement=helpers['PLACEMENT']
spec=geo.read(data/'derived-spec.json'); overlay=geo.read(data/'lower-evidence.json'); floor=geo.read(placement)
assert len(spec['nets'])==1184 and geo.sha(placement)==overlay['placement_sha256']==geo.PLACEMENT_SHA
targets=[r for r in csv.DictReader((plan_dir/'reservations.tsv').open(),delimiter='\t') if r['status']=='fanout_needed']
assert len(targets)==1
target=targets[0]
net=spec['nets'][int(target['net'])]; i=int(target['pin']); pin=(net['driver'],*net['sinks'])[i]
assert pin.split('/')[0]=='C0' and pin not in {r['pin'] for r in overlay['rebound']}
terminal=tuple(spec['pins'][pin][0]); assert len(spec['pins'][pin])==1
_,src,base=helpers['info']('C0',overlay)
area=base['area']; box=floor['boxes_dbu']['C0']; mesh=base['mesh']
_,ports=helpers['offset_shapes'](src,floor['placement_dbu']['C0'],area)
owner,=ports[terminal]; assert owner>=0
with (old/'input.txt').open() as f:
    a,b,c,d,count=map(int,next(f).split()); assert [a,b,c,d]==mesh
    shapes=[]
    for _ in range(count):
        o,l,*r=map(int,next(f).split()); shapes.append((o,l,tuple(r)))
verified=geo.read(old/'fanout-verified.json')
assert geo.sha(old/'paths.txt')==verified['paths_sha256']
checker=geo.Checker(shapes)
current={r['pin']:r for r in overlay['rebound']}
for (_,_,path), record in zip(geo.path_records(old/'paths.txt'),verified['paths']):
    assert current[record['pin']]==record
    additions=geo.shapes_for(record['native_owner'],path,tuple(record['new_m10']),area,geo.STEP)
    for o,l,r in additions: checker.verify(o,l,r)
    for o,l,r in additions: checker.add(o,l,r)
    shapes.extend(additions)
terminals=[tuple(spec['pins'][p][0]) for n in spec['nets'] for p in (n['driver'],*n['sinks'])]
sites=[]; seen=set()
for row in base['sites']:
    x,y,rx,ry=row[:4]; pad=geo.rect((x,y),(x,y),2000)
    if (rx,ry) in seen or not geo.contains(area,pad) or geo.too_close(pad,box,0): continue
    if any(geo.too_close(pad,r,6500) for r in terminals): continue
    seen.add((rx,ry))
    side=max(range(4),key=(box[0]-x,x-box[2],box[1]-y,y-box[3]).__getitem__)
    sites.append((x,y,rx,ry,side))
if mode=='prepare':
    with (output/'input.txt').open('w') as f:
        print(*mesh,len(shapes),file=f)
        for o,l,r in shapes: print(o,l,*r,file=f)
        print(len(sites),file=f)
        for s in sites: print(*s,file=f)
        print(1,file=f); print(1,owner,*terminal,file=f)
    print(pin,'checked candidate sites',len(sites))
else:
    (i,target,path),=geo.path_records(output/'paths.txt'); assert i==1
    x,y,ends_x,ends_y,side=sites[target]
    pad=geo.rect((x,y),(x,y),2000)
    assert path[0][2]==3 and path[-1]==(ends_x,ends_y,3)
    assert geo.contains(terminal,geo.rect(path[0],path[0],800)) and geo.contains(pad,geo.rect(path[-1],path[-1],800))
    for o,l,r in geo.shapes_for(owner,path,pad,area,geo.STEP): checker.verify(o,l,r)
    record={'pin':pin,'net':net['id'],'block':'C0','native_owner':owner,'old_m10':list(terminal),'new_m10':list(pad),
            'landing_side':('west','east','south','north')[side],'paths_sha256':geo.sha(output/'paths.txt')}
    overlay['rebound'].append(record)
    overlay['endpoint_count']=len(overlay['rebound'])
    overlay['route_count']=len({r['net'] for r in overlay['rebound']})
    overlay['focus77_fanout']=record
    geo.write(output/'lower-evidence.json',overlay)
    spec['pins']['frozen_escape_source/'+pin]=[list(terminal)]; spec['pins'][pin]=[list(pad)]
    spec['context']['lower_escape_overlay_sha256']=geo.sha(output/'lower-evidence.json')
    geo.write(output/'derived-spec.json',spec)
    geo.write(output/'fanout.json',record)
    print('fanout_verified',record)
