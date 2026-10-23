"""Conservatively collapse prepaid landings already joined by fixed wires."""
import collections
from freeze_audit import snapshot

def select_accesses(frozen,landings):
    fixed=snapshot(frozen,8)['fixed']
    names={p['net'] for p in landings}
    records=collections.defaultdict(list)
    for key in fixed:
        if key[0] in names:records[key[0]].append(key)
    selected=[];summary=[]
    indexed=collections.defaultdict(list)
    for index,p in enumerate(landings):indexed[p['net']].append((index,p))
    for name,pads in indexed.items():
        parent={}
        def find(p):
            parent.setdefault(p,p)
            if parent[p]!=p:parent[p]=find(parent[p])
            return parent[p]
        def union(a,b):
            a,b=find(a),find(b)
            if a!=b:parent[a]=b
        segments=collections.defaultdict(list)
        for key in records[name]:
            if key[1]=='via':
                _,_,via,x,y=key;low=int(via.split('_')[0][3:])
                union((low,x,y),(low+1,x,y))
            else:
                _,_,layer,x1,y1,e1,x2,y2,e2=key
                union((layer,x1,y1),(layer,x2,y2))
                segments[layer].append((x1,y1,x2,y2))
        # Include T junctions and via contacts in the interior of segments.
        # Centerline evidence is deliberately conservative: no guessed merge
        # through master-pin areas or near but non-touching conductors.
        for layer,lines in segments.items():
            points=[p for p in parent if p[0]==layer]
            for x1,y1,x2,y2 in lines:
                for _,x,y in points:
                    if min(x1,x2)<=x<=max(x1,x2) and min(y1,y2)<=y<=max(y1,y2):
                        union((layer,x1,y1),(layer,x,y))
        groups=collections.defaultdict(list)
        for index,p in pads:groups[find((8,p['x'],p['y']))].append((index,p))
        choice=[]
        if len(groups)>1:
            cx=sum(p['x'] for _,p in pads)/len(pads)
            cy=sum(p['y'] for _,p in pads)/len(pads)
            for group in groups.values():
                index,p=min(group,key=lambda row:(abs(row[1]['x']-cx)+abs(row[1]['y']-cy),row[0]))
                choice.append(index);selected.append(index)
        summary.append(dict(net=name,landings=len(pads),fixed_components=len(groups),selected=choice,
            groups=[[index for index,p in group] for group in groups.values()]))
    return dict(selected=selected,nets=summary,
        source_landings=len(landings),selected_landings=len(selected),
        scope='Only proven same-layer centerline contacts and native fixed vias merge prepaid accesses. All physical access landings remain frozen; unused ones remain upper obstacles. No active or lower-wire changes.')
