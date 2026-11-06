"""Independently check coupon paths, spacing and containment in supplied M10 ports."""
from collections import defaultdict, deque
from itertools import combinations
import json
from pathlib import Path
import re
import sys

H = 2000
WIRE_GAP = 4000
CUT_GAP = 4400

def rect(a, b):
    return min(a[0],b[0])-H,min(a[1],b[1])-H,max(a[0],b[0])+H,max(a[1],b[1])+H

def gap(a,b):
    ax,ay,bx,by=a
    cx,cy,dx,dy=b
    return max(0,ax-dx,cx-bx)**2+max(0,ay-dy,cy-by)**2

def inside(a,b):
    return b[0] <= a[0] <= a[2] <= b[2] and b[1] <= a[1] <= a[3] <= b[3]

def run(path):
    case=path.parent
    proof=json.loads(path.read_text())
    spec=json.loads((case/"inputs.json").read_text())
    targets=spec["macro_endpoint_rects_dbu"]
    txt=(case/"coupon.def").read_text()
    proxy={f"{name}_ready": (int(x),int(y)) for name,x,y in
           re.findall(r"- (\w+)_ready_proxy .*?FIXED \( (\d+) (\d+) \)",txt)}
    errors=[]
    metal,cut=defaultdict(list),defaultdict(list)
    if set(proof["routes"]) | set(proof["failed"]) != set(targets):
        errors.append("net inventory differs from coupon")
    for net, route in proof["routes"].items():
        graph=defaultdict(set)
        nodes=defaultdict(list)
        def link(a,b):
            graph[a].add(b)
            graph[b].add(a)
        for layer,p,q in route["segments"]:
            p,q=tuple(p),tuple(q)
            if layer not in (11,12) or p[1 if layer==11 else 0] != q[1 if layer==11 else 0]:
                errors.append([net,"layer or direction",layer,p,q])
            link((layer,p),(layer,q))
            nodes[layer].append((p,q))
            metal[layer].append((net,rect(p,q)))
        for via_layer in (10,11):
            via_points=[tuple(p) for p in route[f"via{via_layer}"]]
            if len(set(via_points)) != len(via_points):
                errors.append([net,"duplicate via",via_layer])
            for p in via_points:
                link((via_layer,p),(via_layer+1,p))
                r=rect(p,p)
                cut[via_layer].append((net,r))
                for layer in (via_layer,via_layer+1):
                    if layer >=11:
                        metal[layer].append((net,r))
                        for a,b in nodes[layer]:
                            if all(min(x,y)<=v<=max(x,y) for x,y,v in zip(a,b,p)):
                                link((layer,p),(layer,a))
                                link((layer,p),(layer,b))
        via10=[tuple(p) for p in route["via10"]]
        if len(via10)!=len(targets[net]) or any(sum(inside(rect(p,p),r) for p in via10)!=1 for r in targets[net]):
            errors.append([net,"M10 via not enclosed exactly once"])
        expected={(10,p) for p in via10}
        if net in proxy:
            expected.add((11,proxy[net]))
            metal[11].append((net,rect(proxy[net],proxy[net])))
        start=next(iter(expected))
        seen={start}
        queue=deque([start])
        while queue:
            for n in graph[queue.popleft()] - seen:
                seen.add(n)
                queue.append(n)
        if seen != set(graph) or not expected <= seen:
            errors.append([net,"disconnected geometry"])
    for kind, layers, required in (("metal",metal,WIRE_GAP),("cut",cut,CUT_GAP)):
        for layer, shapes in layers.items():
            for (a,ra),(b,rb) in combinations(shapes,2):
                if kind=="metal" and a==b:
                    continue
                if gap(ra,rb)<required**2:
                    errors.append([a,b,kind,layer,ra,rb])
    result=dict(case=case.name,nets=len(targets),routed=len(proof["routes"]),unrouted=sorted(proof["failed"]),
                rule_errors=errors,passes_coupon_geometry=not errors and not proof["failed"],
                native_checks="via10 enclosure in supplied M10 pin rectangles only",
                upper_checks="2 um Manhattan width and spacing, 2.2 um Euclidean same-cut spacing")
    path.with_name(path.stem+"-audit.json").write_text(json.dumps(result,indent=2))
    print(case.name,len(proof["routes"]),len(targets),len(errors),flush=True)

if __name__=="__main__":
    for name in sys.argv[1:]:
        run(Path(name))
