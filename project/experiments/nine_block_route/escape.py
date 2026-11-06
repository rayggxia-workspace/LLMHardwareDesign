"""Find a legal two-layer coupon route with reserved local escapes."""
from collections import defaultdict
import json
from pathlib import Path
import random
import re
import sys

PITCH = 8000
OFFSET = (190, 140)
NEIGHBORS = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
def to_grid(point):
    translated = tuple(c - o for c, o in zip(point, OFFSET))
    if any(c % PITCH for c in translated):
        raise ValueError(f"off-grid point {point}")
    return tuple(c // PITCH for c in translated)

def to_dbu(point):
    return tuple(c * PITCH + o for c, o in zip(point, OFFSET))

class Grid:
    def __init__(self, max_x, max_y):
        self.max_x, self.max_y = max_x, max_y
        self.h = defaultdict(list)
        self.v = defaultdict(list)
        self.cuts = set()

    def legal_segment(self, segment, net):
        layer, a, b = segment
        if layer == 11:
            (x, row), (xx, row2) = a,b
            assert row == row2
            tracks, fixed = self.h, row
        else:
            (fixed, x), (column, xx) = a,b
            assert fixed == column
            tracks = self.v
        lo, hi = sorted((x, xx))
        return all(n == net or hi + 2 <= l or r + 2 <= lo for l,r,n in tracks.get(fixed, ()))

    def legal_via(self, point):
        x,y = point
        return all((x+dx,y+dy) not in self.cuts for dx,dy in NEIGHBORS)

    def commit(self, segments, vias, net):
        for layer, (x1,y1), (x2,y2) in segments:
            tracks, fixed, a,b = (self.h,y1,x1,x2) if layer == 11 else (self.v,x1,y1,y2)
            tracks[fixed].append((*sorted((a,b)), net))
        self.cuts.update(vias)

    def options(self, port, net):
        x,y = port
        for distance in (0,2,3,4,5,6,7,8,10,12,16,20,24,32,48):
            for dx in ((0,) if distance == 0 else (distance,-distance)):
                xc = x+dx
                if not 1 < xc < self.max_x-1:
                    continue
                middle = xc,y
                short = 11,port,middle
                if not self.legal_segment(short, net) or not self.legal_via(middle):
                    continue
                for d in (2,3,4,5,6,7,8,10,12,16,20,24,32,48,64,96,112,128,144,160,180,200,220,240,260,280,320,360,400):
                    for dy in (d,-d):
                        tail = xc,y+dy
                        if not 1 < tail[1] < self.max_y-1 or not self.legal_via(tail):
                            continue
                        stem = 12,middle,tail
                        if self.legal_segment(stem,net):
                            yield tail,[short,stem],[middle,tail]

def run(case, seed):
    spec = json.loads((case/"inputs.json").read_text())
    targets = spec["macro_endpoint_rects_dbu"]
    max_x,max_y = (v//4 for v in spec["die_um"])
    fixed = {}
    for net, rects in targets.items():
        ends = []
        for a,b,c,d in rects:
            if min(c-a,d-b) < 4000:
                raise ValueError(f"landing too small: {net}")
            ends.append(to_grid(((a+c)//2,(b+d)//2)))
        fixed[net] = ends
    text = (case/"coupon.def").read_text()
    for label,x,y in re.findall(r"- (\w+)_ready_proxy .*?FIXED \( (\d+) (\d+) \)",text):
        fixed[f"{label}_ready"].append(to_grid((int(x),int(y))))
    assert all(len(v)==2 for v in fixed.values())
    grid = Grid(max_x,max_y)
    for net,ends in fixed.items():
        grid.commit([(11,p,p) for p in ends],[],net)
    rng = random.Random(seed)
    endpoint_order = [(net, end) for net in fixed for end in range(2)]
    rng.shuffle(endpoint_order)
    # Put the more crowded endpoints first. Commit the small stubs before
    # any full-width segments can consume their local exits.
    def scarce(entry):
        net,i=entry
        p=fixed[net][i]
        x,y=p
        return sum(grid.legal_segment((11,p,(x+dx,y)),net) for dx in (-3,-2,2,3))
    endpoint_order.sort(key=scarce)
    exits={}
    used_rows=set()
    pin_rows={p[1] for ends in fixed.values() for p in ends}
    for net,i in endpoint_order:
        p = fixed[net][i]
        options = list(grid.options(p, net))
        if not options:
            continue
        def cost(entry):
            (x,y),_,_ = entry
            return (10000*(y in used_rows) + 3000*(y in pin_rows) +
                    abs(x-p[0])*2+abs(y-p[1])+rng.random())
        tail,segments,vias=min(options,key=cost)
        used_rows.add(tail[1])
        exits[net,i] = tail,segments,vias
        grid.commit(segments,vias,net)

    def connect(net, a,b):
        ax,ay=a
        bx,by=b
        cols = list(range(2,max_x-2))
        mid=(ax+bx)//2
        cols.sort(key=lambda x: abs(x-mid))
        for xc in cols:
            if ay == by or abs(ay-by) < 2 or abs(xc-ax) < 2 or abs(xc-bx) < 2:
                continue
            c,d=(xc,ay),(xc,by)
            if not grid.legal_via(c) or not grid.legal_via(d):
                continue
            seg=[(11,a,c),(12,c,d),(11,d,b)]
            if all(grid.legal_segment(s,net) for s in seg):
                return seg,[c,d]
        def choices(p):
            x,y=p
            return [col for col in range(max(2,x-160),min(max_x-2,x+161))
                    if abs(col-x)>=2 and grid.legal_via((col,y))
                    and grid.legal_segment((11,p,(col,y)),net)]
        c1,c2=choices(a),choices(b)
        if not c1 or not c2:
            return None
        ys=sorted(range(2,max_y-2),key=lambda y: abs(y-ay)+abs(y-by))
        for y in ys:
            if abs(y-ay)<2 or abs(y-by)<2:
                continue
            l=[x for x in c1 if grid.legal_via((x,y)) and grid.legal_segment((12,(x,ay),(x,y)),net)]
            r=[x for x in c2 if grid.legal_via((x,y)) and grid.legal_segment((12,(x,y),(x,by)),net)]
            for x in l:
                for xx in r:
                    if abs(xx-x)<2 or not grid.legal_segment((11,(x,y),(xx,y)),net):
                        continue
                    p,q,t,w=(x,ay),(x,y),(xx,y),(xx,by)
                    return [(11,a,p),(12,p,q),(11,q,t),(12,t,w),(11,w,b)],[p,q,t,w]
        return None

    routes, failed = {},{}
    order=list(fixed)
    rng.shuffle(order)
    for net in order:
        if (net,0) not in exits or (net,1) not in exits:
            failed[net] = "local escape"
            continue
        a,left,lvia=exits[net,0]
        b,right,rvia=exits[net,1]
        trial=connect(net,a,b)
        if trial is None:
            failed[net] = "trunk"
            continue
        segments,vias=trial
        grid.commit(segments,vias,net)
        routes[net] = dict(
            segments=[(layer,to_dbu(p),to_dbu(q)) for layer,p,q in left+segments+right],
            via11=[to_dbu(p) for p in lvia+vias+rvia],
            via10=[to_dbu(p) for p in fixed[net][:len(targets[net])]],
        )

    out=case/f"escape-{seed}.json"
    out.write_text(json.dumps(dict(routes=routes,failed=failed,units=2000),indent=2))
    print(case.name,seed,len(routes),len(fixed),flush=True)

if __name__ == "__main__":
    run(Path(sys.argv[1]),int(sys.argv[2]))
