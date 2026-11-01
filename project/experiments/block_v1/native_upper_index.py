"""Exact all-net upper-conductor contact audit with a two-axis sweep index.

The grid selects candidate pairs only. Final inclusive contact and native
cut/metal adjacency use the same geometry contract as the exhaustive audit.
No candidate cap, clipping, coordinate snapping or spacing waiver is used.
"""
import collections
import heapq
from native_escape_audit import connected_layers,touching


def audit(by_net,cell_dbu=6400):
    assert type(cell_dbu)is int and cell_dbu>0
    rows=sorted((box[0],box[2],name,layer,kind,box)for name,items in by_net.items()
                for layer,kind,box in items if layer in ('metal9','metal10','via9'))
    buckets=collections.defaultdict(set);active={};expiry=[];shorts=[];pairs=0
    for identity,(x1,x2,name,layer,kind,box)in enumerate(rows):
        while expiry and expiry[0][0]<x1:
            right,old=heapq.heappop(expiry);other,other_layer,other_kind,other_box=active.pop(old)
            for key in range(other_box[1]//cell_dbu,other_box[3]//cell_dbu+1):
                buckets[key].remove(old)
                if not buckets[key]:del buckets[key]
        keys=range(box[1]//cell_dbu,box[3]//cell_dbu+1);candidates=set()
        for key in keys:candidates.update(buckets.get(key,()))
        for other_id in sorted(candidates):
            other,other_layer,other_kind,other_box=active[other_id];pairs+=1
            if name!=other and connected_layers(layer,other_layer)and touching(box,other_box):
                shorts.append(dict(net=name,other=other,layer=layer,other_layer=other_layer,box=box,other_box=other_box))
        active[identity]=(name,layer,kind,box);heapq.heappush(expiry,(x2,identity))
        for key in keys:buckets[key].add(identity)
    return dict(passed=not shorts,shape_count=len(rows),net_count=len(by_net),shorts=shorts,
                index_cell_dbu=cell_dbu,exact_candidate_pair_checks=pairs,
                scope='Complete actual upper wire/via/pin/PG inter-net contact audit; native full-rule DRC and other layers remain separate')
