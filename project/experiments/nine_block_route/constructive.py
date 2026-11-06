"""Construct a conservative Manhattan route on the research upper-layer grid."""
from collections import defaultdict
import json
from pathlib import Path
import random
import re
import sys

PITCH = 8000
OX, OY = 190, 140
HALF = 2000
MIN_TRACK_END_DISTANCE = 8000

case = Path(sys.argv[1])
seed = int(sys.argv[2])
spec = json.loads((case / "inputs.json").read_text())
max_x, max_y = (n * 2000 for n in spec["die_um"])
targets = spec["macro_endpoint_rects_dbu"]
text = (case / "coupon.def").read_text()
proxy = {}
for label, x, y in re.findall(r"- (\w+)_ready_proxy .*?FIXED \( (\d+) (\d+) \)", text):
    proxy[f"{label}_ready"] = int(x), int(y)

def center(rect):
    a,b,c,d = rect
    x,y = (a+c)//2, (b+d)//2
    if c-a < 2*HALF or d-b < 2*HALF:
        raise ValueError(f"insufficient landing {rect}")
    return x,y

points = {net: [center(rect) for rect in rects] for net,rects in targets.items()}
for net, end in proxy.items():
    points[net].append(end)
assert all(len(ends) == 2 for ends in points.values())

def point_on_grid(x,y):
    return (x-OX) % PITCH == (y-OY) % PITCH == 0

class Occupancy:
    def __init__(self):
        self.h = defaultdict(list)
        self.v = defaultdict(list)
        self.cuts = {}

    @staticmethod
    def clear(tracks, fixed, a, b, net):
        lo, hi = sorted((a,b))
        return all(
            other == net or hi + MIN_TRACK_END_DISTANCE <= left or
            right + MIN_TRACK_END_DISTANCE <= lo
            for left,right,other in tracks.get(fixed, ())
        )

    def fits(self, xs, ys, xt, yt, xc, ya, yb, net):
        # Via center pitch and exact 2 um square widths make diagonally
        # adjacent 4 um tracks legal for the declared 2.2 um cut gap.
        via = [(xs,ys),(xs,ya),(xc,ya),(xc,yb),(xt,yb),(xt,yt)]
        if len(set(via)) != len(via):
            return False
        for x,y in via:
            for dx,dy in ((0,0),(0,PITCH),(0,-PITCH),(PITCH,0),(-PITCH,0)):
                if (x+dx,y+dy) in self.cuts or (dx or dy) and (x+dx,y+dy) in via:
                    return False
        return (
            self.clear(self.h, ys, xs, xs, net) and self.clear(self.h, yt, xt, xt, net)
            and self.clear(self.h, ya, xs, xc, net) and self.clear(self.h, yb, xc, xt, net)
            and self.clear(self.v, xs, ys, ya, net) and self.clear(self.v, xc, ya, yb, net)
            and self.clear(self.v, xt, yb, yt, net)
        )

    def add(self, xs, ys, xt, yt, xc, ya, yb, net):
        for track, fixed, a,b in (
            (self.h,ys,xs,xs),(self.h,yt,xt,xt),(self.h,ya,xs,xc),(self.h,yb,xc,xt),
            (self.v,xs,ys,ya),(self.v,xc,ya,yb),(self.v,xt,yb,yt)
        ):
            track[fixed].append((*sorted((a,b)),net))
        for point in ((xs,ys),(xs,ya),(xc,ya),(xc,yb),(xt,yb),(xt,yt)):
            self.cuts[point] = net

occ = Occupancy()
rng = random.Random(seed)
reserved_y = {y for ends in points.values() for x,y in ends}
reserved_x = {x for ends in points.values() for x,y in ends}
landings = {}
for net, ends in points.items():
    for (x,y) in ends:
        if not point_on_grid(x,y):
            raise ValueError(f"{net}: off-grid center {(x,y)}")
        if (x,y) in landings:
            raise ValueError(f"{net}: overlaps {landings[x,y]} at {(x,y)}")
        landings[x,y] = net
for (x,y), net in landings.items():
    for dx,dy in ((0,PITCH),(PITCH,0)):
        if (x+dx,y+dy) in landings:
            raise ValueError(f"{net}: adjacent fixed cuts {landings[x+dx,y+dy]}")
    occ.h[y].append((x,x,net))

order = list(points)
rng.shuffle(order)
routes, failures = {}, {}
for net in order:
    (xs,ys),(xt,yt) = points[net]
    mid = ((xs+xt-2*OX)//(2*PITCH))*PITCH + OX
    trunks = sorted((x for x in range(OX+PITCH,max_x-PITCH,PITCH) if x not in reserved_x),
                    key=lambda x: abs(x-mid))[:96]
    sx = [ys+n*PITCH for n in range(-28,29) if 2 <= abs(n) and PITCH < ys+n*PITCH < max_y-PITCH
          and ys+n*PITCH not in reserved_y]
    tx = [yt+n*PITCH for n in range(-28,29) if 2 <= abs(n) and PITCH < yt+n*PITCH < max_y-PITCH
          and yt+n*PITCH not in reserved_y]
    pairs = sorted(((ya,yb) for ya in sx for yb in tx if ya!=yb),
                   key=lambda ab: abs(ab[0]-ys)+abs(ab[1]-yt))
    trial = next(((xc,ya,yb) for ya,yb in pairs for xc in trunks if
                  occ.fits(xs,ys,xt,yt,xc,ya,yb,net)),None)
    if trial is None:
        failures[net] = {"pins_dbu": points[net], "trunks_tried": len(trunks), "row_pairs":len(pairs)}
        continue
    xc,ya,yb = trial
    occ.add(xs,ys,xt,yt,xc,ya,yb,net)
    routes[net] = [(xs,ys),(xs,ya),(xc,ya),(xc,yb),(xt,yb),(xt,yt)]

def path(net, points):
    a,b,c,d,e,f = points
    def pt(p):
        return f"( {p[0]} {p[1]} )"
    pieces = [f"metal12 {pt(a)} {pt(b)} BV1_via11",
              f"metal11 {pt(b)} {pt(c)} BV1_via11",
              f"metal12 {pt(c)} {pt(d)} BV1_via11",
              f"metal11 {pt(d)} {pt(e)} BV1_via11",
              f"metal12 {pt(e)} {pt(f)} BV1_via11",
              f"metal11 {pt(a)} BV1_via11", f"metal10 {pt(a)} BV1_via10"]
    if net not in proxy:
        pieces.append(f"metal10 {pt(f)} BV1_via10")
    return " + ROUTED " + " NEW ".join(pieces)

def attach(match):
    net = match[2]
    return match[1] + (path(net,routes[net]) if net in routes else "") + " ;"

text = re.sub(r"(^- (\w+) .*?\+ USE SIGNAL) ;$",attach,text,flags=re.M)
label = case / f"constructive-{seed}"
label.with_suffix(".def").write_text(text)
lengths = {net: sum(abs(x1-x2)+abs(y1-y2) for (x1,y1),(x2,y2) in zip(pts,pts[1:]))/2000
           for net,pts in routes.items()}
label.with_suffix(".json").write_text(json.dumps(dict(
    n_expected=len(points), n_routed=len(routes), failed=failures, length_um=lengths,
    stack_model="axis-aligned ideal 2um research", independent_drc=False,
    via11_count=6*len(routes), via10_count=sum(len(targets[n]) for n in routes)
), indent=2))
