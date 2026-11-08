"""Deterministic communication-aware search over legal frozen-patch placements.

Communication uses supplied physical endpoint identities, never model/operator
names. Source-patch prewires are preserved. The returned score is an estimate;
actual route, field RC and timing are mandatory subsequent feedback gates.
"""
from resource_base import assemble,place


def estimate(base,nets):
    total=0
    for net in nets:
        points=[]
        for name in [net['driver']]+net['sinks']:
            r=base['endpoints'][name]['m10_shapes'][0]['rect_dbu']
            points.append(((r[0]+r[2])/2,(r[1]+r[3])/2))
        if points:total+=(max(p[0] for p in points)-min(p[0] for p in points)+
                          max(p[1] for p in points)-min(p[1] for p in points))*net.get('weight',1)
    return total


def optimize(instances,library,nets,*,gap_dbu,alignment_dbu,rounds=8,width=8,aspect=1.):
    if rounds<0 or width<1:raise ValueError('invalid placement search budget')
    initial=tuple(sorted(instances,key=lambda n:(-(library[instances[n]]['inventory']['die'][3]-library[instances[n]]['inventory']['die'][1]),
                                               -(library[instances[n]]['inventory']['die'][2]-library[instances[n]]['inventory']['die'][0]),n)))
    seen={};history=[]
    def evaluate(order):
        if order not in seen:
            pos,bounds=place(instances,library,gap_dbu=gap_dbu,alignment_dbu=alignment_dbu,aspect=aspect,order=order)
            base=assemble(instances,library,pos,bounds)
            score=(estimate(base,nets),(bounds[2]-bounds[0])*(bounds[3]-bounds[1]),order)
            seen[order]=(score,pos,bounds)
        return seen[order]
    evaluate(initial);frontier=[initial]
    for iteration in range(rounds):
        candidates=set(frontier)
        for order in frontier:
            for i in range(len(order)):
                for j in range(i+1,len(order)):
                    other=list(order);other[i],other[j]=other[j],other[i];candidates.add(tuple(other))
        for order in sorted(candidates):evaluate(order)
        frontier=sorted(candidates,key=lambda order:seen[order][0])[:width]
        history.append({'round':iteration,'best_wire_estimate_dbu':seen[frontier[0]][0][0],
                        'best_area_dbu2':seen[frontier[0]][0][1],'evaluated':len(seen)})
        if history and len(history)>1 and history[-1]['evaluated']==history[-2]['evaluated']:break
    best=min(seen,key=lambda order:seen[order][0]);score,pos,bounds=seen[best]
    return pos,bounds,{'initial_order':list(initial),'selected_order':list(best),
                       'initial_wire_estimate_dbu':seen[initial][0][0],'selected_wire_estimate_dbu':score[0],
                       'initial_area_dbu2':seen[initial][0][1],'selected_area_dbu2':score[1],
                       'evaluated':len(seen),'history':history,
                       'qualification':'placement estimate only; physical routes and RC/timing must be checked'}
