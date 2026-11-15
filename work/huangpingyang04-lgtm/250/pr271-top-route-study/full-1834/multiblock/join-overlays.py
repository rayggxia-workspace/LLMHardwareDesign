"""Combine independently checked, disjoint lower overlays into one top handoff."""
import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path

import lower_rules as rules


SEED_SHA="2542c710671fb334c6c03962d4a3a460a13b89cbe4d915b11b82bce07e3cd093"
SEED_LEDGER="d3692dcaf6e33253c985d579fc9b382164c7fd8b0f22e36214a1e9d23ab189ba"
LOCKED_320="9563f3696e9233c8e5cc732546a0668945adb166e762b3ee133f9a1396b11460"
FOCUS={"U0":180,"C0":80,"dma":140,"P0":40,"P1":40,"P2":40,"mc":45}
BLOCKS=set(FOCUS)


def choose(rows, mode, limit):
    if mode=="all":
        return rows
    if mode=="focused":
        return rows[:limit]
    queues=defaultdict(deque)
    for r in rows:
        queues[r["landing_side"]].append(r)
    result=[]
    while len(result)<limit and any(queues.values()):
        for side in ("west","east","south","north"):
            if queues[side]:
                result.append(queues[side].popleft())
                if len(result)==limit:
                    break
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("all","focused","balanced"))
    for k in ("original","base","placement","out"):
        parser.add_argument(k,type=Path)
    parser.add_argument("overlays",type=Path,nargs="+")
    a=parser.parse_args()
    assert rules.sha(a.original)==rules.ORIGINAL_SHA
    assert rules.sha(a.placement)==rules.PLACEMENT_SHA
    lower_hash=rules.sha(a.base/"derived-spec.json")
    lower_ledger=rules.sha(a.base/"lower-evidence.json")
    orig=rules.read(a.original)
    spec=rules.read(a.base/"derived-spec.json")
    previous=rules.read(a.base/"lower-evidence.json")
    assert orig["nets"]==spec["nets"] and len(orig["nets"])==1834
    assert len(previous["rebound"])==previous["route_count"] and 320<=previous["route_count"]<=909
    switch_area=(5450000,6930000,7332000,8445000)
    if lower_hash!=SEED_SHA:
        assert previous["type"]=="continued-m7-m10-geometric-overlay"
        assert previous["locked_escape_sha256"]==LOCKED_320
        assert previous["placement_sha256"]==rules.PLACEMENT_SHA
        assert previous["original_handoff_sha256"]==rules.ORIGINAL_SHA
        assert rules.sha(a.base/"paths.txt")==previous["new_lower_routes_sha256"]
        plan=rules.read(a.base/"plan.json")
        switch_area=tuple(plan["area"])
        assert switch_area in {(5450000,6930000,7332000,8445000),(4350000,6935000,8850000,8445000)}
    else:
        assert lower_ledger==SEED_LEDGER
    box=rules.read(a.placement)["boxes_dbu"]
    assert all(not rules.too_close(switch_area,b,3200) for k,b in box.items() if k!="sw")
    roots={n["id"]:set([n["driver"],*n["sinks"]]) for n in orig["nets"]}
    expected=dict(orig["pins"])
    for v in previous["rebound"]:
        pin=v["pin"]
        assert pin.startswith("sw/") and pin in roots[v["net"]]
        assert expected[pin]==[v["old_m10"]]
        expected["frozen_escape_source/"+pin]=expected[pin]
        expected[pin]=[v["new_m10"]]
    assert spec["pins"]==expected and spec["context"]==dict(orig["context"],lower_escape_overlay_sha256=lower_ledger)
    moved={row["pin"] for row in previous["rebound"]}
    records=list(previous["rebound"])
    modules={}
    occupied=[switch_area]
    for file in a.overlays:
        v=rules.read(file/"block-evidence.json")
        block=v["block"]
        assert block in BLOCKS and block not in modules
        assert rules.sha(file/"paths.txt")==v["routes_sha256"] and v["base_handoff_sha256"]==SEED_SHA
        area=v["area"]
        assert not any(rules.too_close(area,b,3200) for b in occupied)
        occupied.append(area)
        assert v["count"]==len(v["rebound"])
        chosen=choose(v["rebound"],a.mode,FOCUS[block])
        sides=Counter()
        for r in chosen:
            pin=r["pin"]
            assert pin in roots[r["net"]] and pin not in moved and pin.startswith(block+"/")
            assert r["block"]==block and orig["pins"][pin]==spec["pins"][pin]==[r["old_m10"]]
            assert rules.contains(area,r["new_m10"]) and not rules.too_close(r["new_m10"],box[block],0)
            spec["pins"]["frozen_escape_source/"+pin]=spec["pins"][pin]
            spec["pins"][pin]=[r["new_m10"]]
            records.append(r)
            moved.add(pin)
            sides[r["landing_side"]]+=1
        modules[block]={"adopted":len(chosen),"by_side":dict(sides),"available":v["count"],
                        "source":str(file),"block_receipt_sha256":rules.sha(file/"block-evidence.json"),
                        "paths_sha256":v["routes_sha256"]}
    assert set(modules)==BLOCKS and modules["U0"]["adopted"]>=30
    assert len(moved)==len(records)
    result={"type":"multi-block-lower-escape","mode":a.mode,
            "original_handoff_sha256":rules.ORIGINAL_SHA,"placement_sha256":rules.PLACEMENT_SHA,
            "switch_overlay_sha256":lower_ledger,"modules":modules,
            "route_count":len({r["net"] for r in records}),
            "endpoint_count":len(records),"switch_route_count":previous["route_count"],"rebound":records}
    assert "lower_escape_overlay_sha256" in spec["context"]
    rules.write(a.out/"lower-evidence.json",result)
    spec["context"]["lower_escape_overlay_sha256"]=rules.sha(a.out/"lower-evidence.json")
    rules.write(a.out/"derived-spec.json",spec)
    print({k:v for k,v in result.items() if k!="rebound"},flush=True)


if __name__=="__main__":
    main()
