"""Audit the checked end-to-end route sets and mandatory crossings after escape."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(p, box):
    return box[0] < p[0] < box[2] and box[1] < p[1] < box[3]


def outside(p, box):
    return p[0] < box[0] or p[0] > box[2] or p[1] < box[1] or p[1] > box[3]


def audit(upper, lower, previous, placement, original_bound, alternatives):
    spec=read(lower/"derived-spec.json")
    verified=read(upper/"routes.json")
    overlay=read(lower/"lower-evidence.json")
    assert verified["geometry_check"]["passed"]
    assert verified["evidence"]["lower_overlay_sha256"]==sha(lower/"lower-evidence.json")
    floor=read(placement)
    old=read(previous)
    nets=spec["nets"]
    ids={n["id"] for n in nets}
    routed=set(verified["routes"])
    missing=set(verified["failed"])
    former=set(old["routes"])
    assert len(ids)==1834 and ids==routed|missing and not routed&missing and len(former)==688
    old_moved={row["net"] for row in overlay["rebound"][:320]}
    added={row["net"] for row in overlay["rebound"][320:]}
    assert (len(old_moved), len(added))==(320, overlay["additional_count"])
    assert not old_moved&added
    assert len((old_moved|added)&routed)==verified["evidence"]["through_escape"]
    for record in overlay["rebound"]:
        nid,pin=record["net"],record["pin"]
        if nid not in routed:
            continue
        via=next(v["at"] for v in verified["routes"][nid]["via10"] if v["pin"]==pin)
        x1,y1,x2,y2=record["new_m10"]
        assert via==[(x1+x2)//2,(y1+y2)//2]

    grid=iter((upper/"graph.txt").read_text().splitlines())
    assert int(next(grid).split()[-1])==len(nets)
    terminals={}
    dx,dy=spec["technology"]["origin"]
    step=spec["technology"]["access_pitch"]
    for i,n in enumerate(nets):
        j,count,windows=map(int,next(grid).split())
        assert i==j and count==1+len(n["sinks"])
        xy=[tuple(map(int,next(grid).split())) for _ in range(count)]
        terminals[n["id"]]=[(dx+x*step,dy+y*step) for x,y in xy]
        for _ in range(windows):
            next(grid)
    old_cut=read(original_bound)["cuts"]["sw/terminal-center cut"]
    rectangles={**floor["boxes_dbu"], "sw/original-terminal-cut":old_cut["bounds_dbu"]}
    gap=spec["technology"]["width"]+spec["technology"]["spacing"]
    cuts={}
    for label,box in sorted(rectangles.items()):
        p={nid for nid,points in terminals.items()
           if any(inside(point,box) for point in points) and any(outside(point,box) for point in points)}
        cap=2*((box[2]-box[0])//gap+1+(box[3]-box[1])//gap+1)
        cuts[label]={"required":len(p),"capacity_upper_bound":cap,"deficit":max(0,len(p)-cap),
                     "already_routed":len(p&routed),"still_unrouted":len(p&missing)}
    on_sw=cuts["sw"]
    assert on_sw["required"]==overlay["top_only_sw_crossings"]
    witnessed=set()
    for path in alternatives:
        other=read(path/"routes.json")
        assert other["geometry_check"]["passed"] and other["context"]==verified["context"]
        witnessed.update(set(other["routes"]) & missing)
    return {
        "end_to_end":len(routed),"unrouted":len(missing),
        "already_routed_in_previous_best":len(former&routed),
        "not_routed_in_previous_best_but_now_routed":len(routed-former),
        "routed_in_previous_best_but_unrouted_here":len(former-routed),
        "verified_old_escape_end_to_end":len(old_moved&routed),
        "verified_new_escape_end_to_end":len(added&routed),
        "remaining_proven_in_other_upper_orders_same_landings":len(witnessed),
        "other_upper_orders_compared":len(alternatives),"cuts":cuts
    }


if __name__=="__main__":
    args=argparse.ArgumentParser(description=__doc__)
    for name in ("upper","lower","previous","placement","cut"):
        args.add_argument(name,type=Path)
    args.add_argument("other",type=Path,nargs="*")
    a=args.parse_args()
    print(json.dumps(audit(a.upper,a.lower,a.previous,a.placement,a.cut,a.other),sort_keys=True))
