"""Audit fixed and local rectangle capacity on one admitted top-level track graph."""
import argparse
from collections import Counter
import json
from pathlib import Path


def cell_positions(lo,hi,offset,pitch):
    return range(lo+(offset-lo)%pitch,hi+1,pitch)


def side_limit(cut,lo,hi,axis,origin,step,tp,gap,windows):
    across=1-axis
    candidates=set(cell_positions(lo,hi,origin[across],tp))
    for w in windows:
        if w[axis]<=cut<=w[axis+2]:
            candidates.update(cell_positions(max(lo,w[across]),min(hi,w[across+2]),origin[across],step))
    last=lo-gap
    total=0
    for x in sorted(candidates):
        if x-last>=gap:
            total+=1
            last=x
    return total


def read(path):
    return json.loads(path.read_bytes())


def audit(spec_dir,placement,routes=None,extra_boxes=()):
    spec=read(spec_dir/"derived-spec.json")
    t=spec["technology"]
    floor=read(placement)
    ox,oy=t["origin"]
    step=t["access_pitch"]
    tp=t["pitch"]
    gap=t["width"]+t["spacing"]
    xs=[]
    net_centers=[]
    windows=[]
    source=iter((spec_dir/"graph.txt").read_text().splitlines())
    assert int(next(source).split()[-1])==len(spec["nets"])==1834
    for i,n in enumerate(spec["nets"]):
        j,np,nw=map(int,next(source).split())
        assert i==j and np==1+len(n["sinks"])
        points=[]
        for _ in range(np):
            x,y=map(int,next(source).split())
            points.append((ox+x*step,oy+y*step))
        xs.extend(points)
        net_centers.append((n["id"],points))
        for _ in range(nw):
            l,b,r,t0=map(int,next(source).split())
            windows.append((ox+l*step,oy+b*step,ox+r*step,oy+t0*step))
    xlim,ylim,xmax,ymax=t["bounds"]
    bins=Counter((x//160000,y//160000) for x,y in xs)
    local=set()
    for (i,j),_ in bins.most_common(36):
        x=(i*2+1)*80000
        y=(j*2+1)*80000
        for h,v in [(80000,80000),(160000,80000),(80000,160000),
                    (180000,180000),(320000,180000),(180000,320000),(350000,350000)]:
            local.add((max(xlim,x-h),max(ylim,y-v),min(xmax,x+h),min(ymax,y+v)))
    checked=read(routes) if routes else None
    if checked:
        assert checked["geometry_check"]["passed"] and checked["context"]==spec["context"]
    route_ids=set(checked["routes"]) if checked else set()
    def score(box):
        l,b,r,t0=box
        must={nid for nid,pts in net_centers
              if any(l<x<r and b<y<t0 for x,y in pts)
              and any(x<l or x>r or y<b or y>t0 for x,y in pts)}
        args=((ox,oy),step,tp,gap,windows)
        sides=[side_limit(x,b,t0,0,*args) for x in (l,r)]+[side_limit(y,l,r,1,*args) for y in (b,t0)]
        capacity=sum(sides)
        return {"box_dbu":box,"required":len(must),"optimistic_capacity":capacity,
                "slack":capacity-len(must),"routed":len(must&route_ids),
                "sides":sides}
    macros={label:score(box) for label,box in floor["boxes_dbu"].items()}
    local_results=sorted((score(box) for box in local),key=lambda x:x["slack"])
    result={"macro_cuts":macros,"local_rectangles_checked":len(local),
            "worst_local":local_results[:12],"negative_local_count":sum(x["slack"]<0 for x in local_results)}
    if extra_boxes:
        result["requested_rectangles"]=[score(tuple(box)) for box in extra_boxes]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("spec",type=Path)
    p.add_argument("placement",type=Path)
    p.add_argument("--routes",type=Path)
    p.add_argument("--rectangle",type=int,nargs=4,action="append",default=[])
    a=p.parse_args()
    print(json.dumps(audit(a.spec,a.placement,a.routes,a.rectangle),sort_keys=True))
