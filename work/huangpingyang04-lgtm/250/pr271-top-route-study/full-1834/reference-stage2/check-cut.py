"""Recount mandatory cut crossings and matched routed nets from exported landings."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capacity_on_one_side(cut, low, high, axis, origin, lattice_pitch, track_pitch, gap, windows):
    """Optimistic count using the union of every active net's off-track windows."""
    def lattice(first, last, offset, pitch):
        return range(first+(offset-first)%pitch,last+1,pitch)

    alternative_axis=1-axis
    candidates=set(lattice(low,high,origin[alternative_axis],track_pitch))
    for window in windows:
        if window[axis]<=cut<=window[axis+2]:
            begin=max(low,window[alternative_axis])
            end=min(high,window[alternative_axis+2])
            candidates.update(lattice(begin,end,origin[alternative_axis],lattice_pitch))
    last=low-gap
    count=0
    for position in sorted(candidates):
        if position-last>=gap:
            count+=1
            last=position
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("run","spec","placement","old_cut"):
        p.add_argument(name,type=Path)
    args=p.parse_args()
    routes=read(args.run/"routes.json")
    assert routes["geometry_check"]["passed"]
    spec=read(args.spec)
    assert routes["context"]==spec["context"]
    placement=read(args.placement)
    original_inner=read(args.old_cut)["cuts"]["sw/terminal-center cut"]["bounds_dbu"]
    cuts={"switch_outline":placement["boxes_dbu"]["sw"],"switch_inner_original":original_inner,
          "U0_outline":placement["boxes_dbu"]["U0"],"DMA_outline":placement["boxes_dbu"]["dma"]}
    members={name:set() for name in cuts}
    all_windows=[]
    tx,ty=spec["technology"]["origin"]
    pitch=spec["technology"]["access_pitch"]
    with (args.run/"graph.txt").open() as graph:
        assert int(next(graph).split()[-1])==len(spec["nets"])==1834
        for index,net in enumerate(spec["nets"]):
            i,n,windows=map(int,next(graph).split())
            assert i==index and n==1+len(net["sinks"])
            xy=[list(map(int,next(graph).split())) for _ in range(n)]
            ids=[(tx+x*pitch,ty+y*pitch) for x,y in xy]
            for _ in range(windows):
                l,b,r,t=map(int,next(graph).split())
                all_windows.append((tx+l*pitch,ty+b*pitch,tx+r*pitch,ty+t*pitch))
            for name,(l,b,r,t) in cuts.items():
                inside=any(l<x<r and b<y<t for x,y in ids)
                outside=any(x<l or x>r or y<b or y>t for x,y in ids)
                if inside and outside: members[name].add(net["id"])
    gap=spec["technology"]["width"]+spec["technology"]["spacing"]
    result={}
    for name,(l,b,r,t) in cuts.items():
        demand=members[name]
        capacity=2*((r-l)//gap+(t-b)//gap+2)
        args_static=((tx,ty),pitch,spec["technology"]["pitch"],gap,all_windows)
        grid_capacity=(sum(capacity_on_one_side(x,b,t,0,*args_static) for x in (l,r))
                       +sum(capacity_on_one_side(y,l,r,1,*args_static) for y in (b,t)))
        assert grid_capacity<=capacity
        result[name]={"mandatory":len(demand),"capacity_upper_bound":capacity,
                      "minimum_deficit":max(0,len(demand)-capacity),
                      "graph_capacity_upper_bound":grid_capacity,
                      "graph_minimum_deficit":max(0,len(demand)-grid_capacity),
                      "routed":len(demand&routes["routes"].keys()),
                      "unrouted":len(demand&routes["failed"].keys())}
    print(json.dumps({"source_graph_sha256":sha(args.run/"graph.txt"),
                      "routes_sha256":sha(args.run/"routes.json"),
                      "cuts":result},sort_keys=True))


if __name__=="__main__":
    main()
