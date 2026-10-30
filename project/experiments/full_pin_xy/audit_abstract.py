"""Check exported LEF rectangles without inferring parent routing accessibility.

Reports positive-area same-layer PIN/OBS overlap. This is a diagnostic, not a
complete LEF access rule or a declaration of physical infeasibility.
"""
import argparse,hashlib,json,math,re
from collections import defaultdict
from pathlib import Path

def audit(path):
    path=Path(path);pins=defaultdict(list);obs=defaultdict(list)
    pin=None;layer=None;inside_obs=False
    for line in path.read_text().splitlines():
        t=line.split()
        if not t:continue
        if t[0]=='PIN':pin=t[1];inside_obs=False
        elif t[0]=='OBS':pin=None;inside_obs=True
        elif t[0]=='LAYER':layer=t[1]
        elif t[0] in ('POLYGON','PATH','VIA'):raise ValueError('Unsupported geometry; do not silently omit: '+line)
        elif t[0]=='RECT':
            r=tuple(map(float,t[1:5]));assert len(r)==4 and r[0]<r[2] and r[1]<r[3]
            if pin:pins[pin].append((layer,r))
            elif inside_obs:obs[layer].append(r)
        elif t[0]=='END':
            if len(t)>1 and t[1]==pin:pin=None
            elif inside_obs and len(t)==1:inside_obs=False
    # Spatial index includes large rectangles, avoiding a per-pin full scan.
    bins=defaultdict(set);step=8.0
    def keys(layer,r):
        for x in range(math.floor(r[0]/step),math.floor(r[2]/step)+1):
            for y in range(math.floor(r[1]/step),math.floor(r[3]/step)+1):yield layer,x,y
    for layer,rs in obs.items():
        for n,r in enumerate(rs):
            for k in keys(layer,r):bins[k].add(n)
    overlaps={}
    for name,shapes in pins.items():
        hits=[]
        for layer,r in shapes:
            ids=set().union(*(bins[k] for k in keys(layer,r)))
            for n in ids:
                q=obs[layer][n];dx=min(r[2],q[2])-max(r[0],q[0]);dy=min(r[3],q[3])-max(r[1],q[1])
                if dx>1e-9 and dy>1e-9:hits.append({'layer':layer,'pin_rectangle_um':r,'OBS_rectangle_um':q,'overlap_area_um2':dx*dy})
        if hits:overlaps[name]=hits
    return {'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pin_count_including_PG':len(pins),
        'OBS_rectangles_by_layer':{k:len(v) for k,v in obs.items()},'pins_overlapping_same_layer_OBS':len(overlaps),'overlaps':overlaps,
        'scope':'Exact positive-area rectangle intersections only; not via enclosure, spacing, parent handoff, route accessibility, GDS/LVS or full rule qualification.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('lef');p.add_argument('--out',required=True);a=p.parse_args()
    r=audit(a.lef);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print('ABSTRACT_DIAGNOSTIC',r['pin_count_including_PG'],r['pins_overlapping_same_layer_OBS'])
