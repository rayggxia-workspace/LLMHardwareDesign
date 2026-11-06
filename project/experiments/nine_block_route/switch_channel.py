"""Construct an upper route with a dedicated horizontal lane per terminal."""

from bisect import bisect_left
import json
from pathlib import Path
import random
import re
import sys

from escape import Grid, to_dbu, to_grid


def near(rows, y):
    """Yield free rows in order of distance from the terminal."""
    r = bisect_left(rows, y)
    l = r - 1
    while l >= 0 or r < len(rows):
        if r == len(rows) or (l >= 0 and y-rows[l] <= rows[r]-y):
            yield rows[l]
            l -= 1
        else:
            yield rows[r]
            r += 1


def route(case, seed):
    spec_path = case/"inputs.json"
    spec = json.loads(spec_path.read_text())
    fixed = {}
    for net, rects in spec["macro_endpoint_rects_dbu"].items():
        fixed[net] = [to_grid(((a+c)//2,(b+d)//2)) for a,b,c,d in rects]
    width, height = spec["die_um"]
    corridor = width//4 + 8
    new_width = 4*(corridor + 2*len(fixed) + 8)
    new_height = max(height, 8*len(fixed)+4096)
    spec["die_um"] = [new_width,new_height]
    spec_path.write_text(json.dumps(spec,indent=2)+"\n")
    def_path = case/"coupon.def"
    text = def_path.read_text()
    text, count = re.subn(r"^DIEAREA .*$",
                         f"DIEAREA ( 0 0 ) ( {new_width*2000} {new_height*2000} ) ;",text, flags=re.M)
    if count != 1:
        raise ValueError("Expected one die boundary in DEF")
    def_path.write_text(text)

    local = Grid(corridor-2,new_height//4,compact=True)
    pin_rows = {p[1] for ends in fixed.values() for p in ends}
    free_rows = sorted(set(range(2,local.max_y-2)) - pin_rows)
    for net, ends in fixed.items():
        local.commit([(11,p,p) for p in ends],[],net)
    rng = random.Random(seed)
    order = [(net, i) for net in fixed for i in range(2)]
    rng.shuffle(order)
    order.sort(key=lambda key: sum(
        local.legal_segment((11,fixed[key[0]][key[1]],(fixed[key[0]][key[1]][0]+dx,
                                                    fixed[key[0]][key[1]][1])),key[0])
        for dx in (-2,-1,1,2)
    ))
    exits = {}
    for net, i in order:
        p = fixed[net][i]
        x,y = p
        other = exits.get((net,1-i))
        best = None
        for distance in local.escape_steps:
            for dx in ((0,) if distance == 0 else (distance,-distance)):
                m = x+dx,y
                if not 1 < m[0] < local.max_x-1:
                    continue
                stub = 11,p,m
                if not local.legal_segment(stub,net) or not local.legal_via(m):
                    continue
                if not local.legal_segment((12,m,m),net):
                    continue
                for j, row in enumerate(near(free_rows,y)):
                    if j >= 640:
                        break
                    cost = abs(row-y)+2*distance
                    if best is not None and cost >= best[0]:
                        break
                    if abs(row-y) < 2 or (other and abs(other[1][1]-row) < 2):
                        continue
                    tail = m[0],row
                    stem = 12,m,tail
                    if local.legal_via(tail) and local.legal_segment(stem,net):
                        best = cost,tail,[stub,stem],[m,tail]
                        break
        if best is not None:
            _,tail,segments,vias = best
            free_rows.pop(bisect_left(free_rows,tail[1]))
            local.commit(segments,vias,net)
            exits[net,i] = best
    routes, failed = {}, {}
    for j, (net, pins) in enumerate(fixed.items()):
        if (net,0) not in exits or (net,1) not in exits:
            failed[net] = "local escape to dedicated channel"
            continue
        _,a,left,lv = exits[net,0]
        _,b,right,rv = exits[net,1]
        x = corridor+2*j
        c,d = (x,a[1]),(x,b[1])
        paths = left + [(11,a,c),(12,c,d),(11,d,b)] + right
        routes[net] = dict(segments=[(layer,to_dbu(s),to_dbu(t)) for layer,s,t in paths],
                           via11=[to_dbu(v) for v in lv+[c,d]+rv],
                           via10=[to_dbu(v) for v in pins])
    (case/f"escape-{seed}.json").write_text(json.dumps(
        dict(routes=routes,failed=failed,units=2000),indent=2)+"\n")
    print(case.name,seed,len(routes),len(fixed),flush=True)


if __name__ == "__main__":
    route(Path(sys.argv[1]),int(sys.argv[2]))
