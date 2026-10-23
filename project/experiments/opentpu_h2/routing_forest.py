"""Preserve connectivity through prepaid lower wires without upper bypasses."""
import collections
from access_components import select_accesses
from freeze_audit import snapshot

def plan_forest(source,frozen,landings):
    lower=select_accesses(frozen,landings)
    shapes=snapshot(source,8)['custom']
    bynet=collections.defaultdict(list)
    for key in shapes:bynet[key[0]].append(key)
    pads=collections.defaultdict(list)
    for index,p in enumerate(landings):pads[p['net']].append((index,p))
    forests=[];proofs=[]
    for low in lower['nets']:
        name=low['net'];parent={}
        def find(p):
            parent.setdefault(p,p)
            if parent[p]!=p:parent[p]=find(parent[p])
            return parent[p]
        def union(a,b):
            a,b=find(a),find(b)
            if a!=b:parent[a]=b
        lines=collections.defaultdict(list)
        for key in bynet[name]:
            if key[1]=='via':
                _,_,via,x,y=key;layer=int(via.split('_')[0][3:])
                union((layer,x,y),(layer+1,x,y))
            else:
                _,_,layer,x1,y1,e1,x2,y2,e2=key
                union((layer,x1,y1),(layer,x2,y2));lines[layer].append((x1,y1,x2,y2))
        for index,p in pads[name]:find((8,p['x'],p['y']))
        for layer,segments in lines.items():
            points=[p for p in parent if p[0]==layer]
            for x1,y1,x2,y2 in segments:
                for _,x,y in points:
                    if min(x1,x2)<=x<=max(x1,x2) and min(y1,y2)<=y<=max(y1,y2):union((layer,x1,y1),(layer,x,y))
        groups=collections.defaultdict(list)
        for index,p in pads[name]:groups[find((8,p['x'],p['y']))].append(index)
        upper=[group for group in groups.values() if len(group)>1]
        # Independent graph layer: union only group membership, not geometry.
        graph={i:i for i,p in pads[name]}
        def root(i):
            while graph[i]!=i:i=graph[i]
            return i
        for group in low['groups']+upper:
            for i in group[1:]:graph[root(i)]=root(group[0])
        connected=len({root(i) for i in graph})==1
        proofs.append(dict(net=name,lower_components=low['fixed_components'],
            upper_forests=len(upper),landings=len(graph),connected=connected))
        assert connected,'Source access graph disconnected: '+name
        for group in upper:
            first=landings[group[0]];component=find((8,first['x'],first['y']))
            nodes=[node for node in parent if find(node)==component]
            box=[max(0,min(p[1] for p in nodes)-13440),max(0,min(p[2] for p in nodes)-13440),
                min(3340000,max(p[1] for p in nodes)+13440),min(3340000,max(p[2] for p in nodes)+13440)]
            forests.append(dict(proxy='h2_forest_'+str(len(forests)),original_net=name,landings=group,guide_box=box))
    return dict(forests=forests,proofs=proofs,passed=all(p['connected'] for p in proofs),
        source_landings=len(landings),forest_count=len(forests),
        scope='Native upper connected components routed separately; their original net identity is restored at integration. Lower-wire connected components join the forests physically. No new active device, access or lower conductor.')
