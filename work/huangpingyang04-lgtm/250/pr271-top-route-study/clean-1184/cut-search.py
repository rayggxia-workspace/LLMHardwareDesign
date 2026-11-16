"""Screen focused rectangular cuts using continuous, optimistic track capacity."""
from collections import Counter
from bisect import bisect_left, bisect_right
import json
from pathlib import Path
import sys

spec = json.loads(Path(sys.argv[1]).read_bytes())
assert len(spec['nets']) == 1184
tech = spec['technology']
between = tech['width'] + tech['spacing']
groups = []
for n in spec['nets']:
    positions = []
    for pin in (n['driver'], *n['sinks']):
        (xl,yl,xh,yh), = spec['pins'][pin]
        positions.append(((xl+xh)//2, (yl+yh)//2))
    groups.append(positions)
positions = sorted((x,y,i) for i,g in enumerate(groups) for x,y in g)
x = [row[0] for row in positions]
sizes = [len(g) for g in groups]
bounds = tech['bounds']
boxes=set()
scales = (16000,24000,32000,48000,64000,96000,144000,200000,280000,400000,560000)
centers=set()
for scale in (32000,64000,128000,224000,320000):
    bins=Counter((a//scale,b//scale) for a,b,_ in positions)
    centers.update((i*scale+scale//2,j*scale+scale//2) for (i,j),n in bins.most_common(128) if n>=4)
for cx,cy in centers:
    for wx in scales:
        for wy in scales:
            if wy > 4*wx or wx > 4*wy:
                continue
            boxes.add((max(bounds[0],cx-wx),max(bounds[1],cy-wy),
                       min(bounds[2],cx+wx),min(bounds[3],cy+wy)))
worst=[]
for xl,yl,xh,yh in boxes:
    count = Counter(net for _,y,net in positions[bisect_right(x,xl):bisect_left(x,xh)] if yl<y<yh)
    required = sum(n<sizes[net] for net,n in count.items())
    capacity = 2*((xh-xl)//between+1) + 2*((yh-yl)//between+1)
    worst.append((capacity-required,required,capacity,(xl,yl,xh,yh)))
worst.sort()
print(json.dumps({'cuts':len(boxes),'deficits':sum(row[0]<0 for row in worst),'worst':worst[:16]}))
