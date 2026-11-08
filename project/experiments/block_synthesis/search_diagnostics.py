"""Certified optimistic bounds for the current candidate/action family.

These bounds do not limit future tiling, residency or finer service calendars.
They help distinguish a search failure from an excessively rigid action model.
"""
import argparse
import json
import math
from pathlib import Path
from verify_loop_dp import verify


def bounds(tasks,hardware,plan):
    verify(tasks,hardware,plan)
    # Prefix reuse can only reduce a binding as far as its all-hit endpoint.
    lower={t['id']:min(b.get('warm_ticks',b['ticks']) for b in t['bindings']) for t in tasks}
    resources={}; mandatory={}
    for t in tasks:
        required=set.intersection(*(set(b['resources']) for b in t['bindings']))
        for resource in required:
            mandatory.setdefault(resource,[]).append(t)
    for resource,assigned in mandatory.items():
        capacity=hardware['resources'][resource]
        work=sum(lower[t['id']] for t in assigned)
        resources[resource]={'mandatory_tasks':len(assigned),'minimum_reserved_work':work,
            'capacity':capacity,'completion_lower_bound':(work+capacity-1)//capacity}
    finish={};pending={t['id']:t for t in tasks}
    while pending:
        ready=[t for t in pending.values() if all(p in finish for p in t.get('after',[]))]
        if not ready:raise ValueError('diagnostic dependency cycle')
        for t in ready:
            finish[t['id']]=lower[t['id']]+max((finish[p] for p in t.get('after',[])),default=0)
            del pending[t['id']]
    critical=max(finish.values(),default=0)
    best=max([critical]+[r['completion_lower_bound'] for r in resources.values()])
    if best>plan['makespan']:raise ValueError('invalid lower bound exceeds verified schedule')
    return {'verified_plan_makespan':plan['makespan'],'critical_path_lower_bound':critical,
        'mandatory_resource_bounds':resources,'completion_lower_bound':best,
        'maximum_time_reduction_fraction_with_current_actions':1-best/plan['makespan'],
        'assumptions':'same atomic kernel candidates, resources, optimistic all-hit cache endpoints; no finer phase/tiling or new hardware',
        'scope':'proof within current serial-kernel action family; not a physical performance or global hardware bound'}


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();ir=json.loads(a.ir.read_text());plan=json.loads(a.plan.read_text())
    result=bounds(ir['tasks'],ir['hardware'],plan)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('verified_plan_makespan','completion_lower_bound','maximum_time_reduction_fraction_with_current_actions')}))


if __name__=='__main__':main()
