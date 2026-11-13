"""Do not let one relaxed program borrow mutually exclusive product metals.

Enumerate maximal unions of complete candidate bundles, extending the exact
minimal completion antichain. A final product's action pool is contained in
one such maximal pool. The minimum of their individual lower bounds is thus
a lower bound for every legal product. Never certify a truncated enumeration.
This is a diagnostic, not another DP or a claim that a topology is routable.
"""
import argparse
import json
from pathlib import Path

from search_diagnostics import relaxation
from static_wiring import completion_covers
from verify_loop_dp import verify


def maximal_unions(tasks,hardware,budget,*,limit=4096):
    if limit<1:raise ValueError('positive topology enumeration limit required')
    covers=completion_covers(tasks,hardware,wire_budget=budget,limit=limit)
    if covers is None:return None
    fixed=frozenset(n for n,v in hardware['nets'].items() if v.get('fixed'))
    alternatives={frozenset(b['nets'])-fixed for t in tasks for b in t['bindings']}
    pairs=tuple(frozenset(p) for p in hardware.get('incompatible_nets',[]))
    def legal(nets):
        return sum(hardware['nets'][n]['cost'] for n in nets)<=budget and not any(p<=nets|fixed for p in pairs)
    alternatives=sorted((a for a in alternatives if legal(a)),key=lambda s:(len(s),tuple(sorted(s))))
    seen=set(covers);todo=list(covers);maximal=set()
    while todo:
        old=todo.pop();extended=False
        for a in alternatives:
            new=old|a
            if new==old or not legal(new):continue
            extended=True
            if new not in seen:
                seen.add(new);todo.append(new)
                if len(seen)>limit:return None
        if not extended:maximal.add(old)
    # No selected unused wire adds an executable binding. Omitting such wires
    # is a valid relaxation; fixed wires are always included in each pool.
    return tuple(sorted((s|fixed for s in maximal),key=lambda s:(len(s),tuple(sorted(s)))))


def diagnose(tasks,hardware,plan,wire_budget,*,limit=4096):
    verify(tasks,hardware,plan,wire_budget=wire_budget)
    unconstrained=relaxation(tasks,hardware)
    unions=maximal_unions(tasks,hardware,wire_budget,limit=limit)
    result={'passed':True,'verified_plan_makespan':plan['makespan'],'wire_budget':wire_budget,
        'unconditioned_completion_lower_bound':unconstrained['completion_lower_bound'],
        'enumeration_complete':unions is not None,'enumeration_limit':limit,
        'scope':'same candidate family and complete static bundle unions; all-hit timing relaxations, no route/system/energy qualification'}
    if unions is None:
        result.update(topologies=None,completion_lower_bound=unconstrained['completion_lower_bound'])
    else:
        if not unions:raise ValueError('verified plan but no complete topology')
        profiles={}
        for nets in unions:
            filtered=[{**t,'bindings':[b for b in t['bindings'] if set(b['nets'])<=nets]} for t in tasks]
            if any(not t['bindings'] for t in filtered):raise ValueError('completion omitted a task')
            r=relaxation(filtered,hardware)
            profiles[tuple(sorted(nets))]=r
        lower=min(r['completion_lower_bound'] for r in profiles.values())
        result.update(topologies=[{'nets':list(nets),**r} for nets,r in profiles.items()],
            topology_count=len(unions),completion_lower_bound=max(unconstrained['completion_lower_bound'],lower))
    if result['completion_lower_bound']>plan['makespan']:raise ValueError('topology lower bound exceeds verified schedule')
    result['maximum_time_reduction_fraction_with_current_actions']=1-result['completion_lower_bound']/plan['makespan']
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--wire-budget',required=True,type=int)
    p.add_argument('--limit',type=int,default=4096);a=p.parse_args()
    ir=json.loads(a.ir.read_text());plan=json.loads(a.plan.read_text())
    result=diagnose(ir['tasks'],ir['hardware'],plan,a.wire_budget,limit=a.limit)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='topologies'}))


if __name__=='__main__':main()
