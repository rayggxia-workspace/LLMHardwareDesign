"""Explain a checked schedule's resource-order critical chain.

This is a diagnostic relaxation, not a replacement scheduler. Fixed-offset
services are split at their resource boundaries, so this graph may allow
extra waiting between stages that the actual rigid service does not allow.
Its longest path is a lower bound for this selected resource order only.
It is neither a global action-family bound nor a demonstrated speedup.
"""
import argparse
from collections import Counter,defaultdict
import heapq
import json
from pathlib import Path

from column_shards import leaf_rows
from dynamic_columns import resized
from verify_loop_dp import verify


def execution_units(tasks,plan):
    by_id={t['id']:t for t in tasks};units=[];owners={}
    for row in plan['tasks']:
        task=by_id[row['id']]
        b=next(b for b in task['bindings'] if b['id']==row['binding'])
        # Cooperative phase compounds lease their entire union throughout;
        # flattening their uncontended children would lose that constraint.
        if 'parallel_shards' in b and 'phase_execution' not in b:
            children=b['parallel_shards']['children']
            if 'frontier_partition' in b:
                children=[resized(c,*r) for c,r in zip(children,row['evaluation']['resolved_columns'])]
            selected=[(r,c['binding']) for r,c in zip(leaf_rows(row),children)]
        else:selected=[(row,b)]
        owners[task['id']]=[]
        for r,binding in selected:
            ident=len(units);owners[task['id']].append(ident)
            units.append({'id':ident,'source':task['id'],'row':r,'binding':binding,
                          'after_tasks':task.get('after',[])})
    for unit in units:
        unit['parents']=[n for t in unit.pop('after_tasks') for n in owners[t]]
    return units


def profile(tasks,hardware,plan,*,operators=None):
    audit=verify(tasks,hardware,plan)
    units=execution_units(tasks,plan);times=[0];edges=[[]];indegree=[0]
    events={};claims=defaultdict(list);segment_work=Counter()
    def vertex(at):
        ident=len(times);times.append(at);edges.append([]);indegree.append(0);return ident
    def edge(a,b,weight,kind,owner=None,resource=None):
        if times[a]+weight>times[b]:raise ValueError('diagnostic constraint contradicts actual times')
        edges[a].append((b,weight,kind,owner,resource));indegree[b]+=1
    for u in units:
        row=u['row'];b=u['binding'];duration=row['end']-row['start']
        offsets=b.get('materialized_tile',{}).get('resource_offsets',{})
        points={0,duration}
        for resource in b['resources']:
            lo,hi=offsets.get(resource,(0,duration));points.update((lo,hi))
            if not 0<=lo<hi<=duration:raise ValueError('invalid selected diagnostic claim')
            claims[resource].append((row['start']+lo,row['start']+hi,u['id'],lo,hi))
        points=sorted(points);ev={}
        for offset in points:
            # A release precedes an acquire at the same timestamp. Separating
            # them avoids spurious zero-time cycles when resources hand over.
            release=vertex(row['start']+offset);acquire=vertex(row['start']+offset)
            ev[offset]=(release,acquire);edge(release,acquire,0,'boundary')
        for lo,hi in zip(points,points[1:]):
            edge(ev[lo][1],ev[hi][0],hi-lo,'service',u['id'])
            segment_work[u['source']]+=hi-lo
        events[u['id']]=ev;edge(0,ev[0][0],0,'source')
    for u in units:
        for parent in u['parents']:
            last=units[parent]['row']['end']-units[parent]['row']['start']
            edge(events[parent][last][0],events[u['id']][0][1],0,'dependency',u['id'])
    for resource,intervals in claims.items():
        capacity=hardware['resources'][resource];slots=[(0,i,None,None) for i in range(capacity)]
        heapq.heapify(slots)
        for start,end,owner,lo,hi in sorted(intervals):
            free,slot,previous,offset=heapq.heappop(slots)
            if free>start:raise ValueError('selected diagnostic resource overlap '+resource)
            if previous is not None:
                edge(events[previous][offset][0],events[owner][lo][1],0,'resource',owner,resource)
            heapq.heappush(slots,(end,slot,owner,hi))
    queue=[i for i,n in enumerate(indegree) if n==0];heapq.heapify(queue)
    distance=[0]*len(times);back=[None]*len(times);seen=0
    while queue:
        a=heapq.heappop(queue);seen+=1
        for b,w,kind,owner,resource in edges[a]:
            if distance[a]+w>distance[b] or back[b] is None:
                distance[b]=distance[a]+w;back[b]=(a,w,kind,owner,resource)
            indegree[b]-=1
            if indegree[b]==0:heapq.heappush(queue,b)
    if seen!=len(times):raise ValueError('selected diagnostic graph cycle')
    terminal=max(range(len(times)),key=lambda i:distance[i]);lower=distance[terminal]
    if lower>plan['makespan']:raise ValueError('selected-order lower bound exceeds verified plan')
    chain=[];by_source=Counter();by_op=Counter();blockers=Counter()
    while back[terminal] is not None:
        previous,w,kind,owner,resource=back[terminal]
        if kind=='service':
            u=units[owner];name=u['source'];by_source[name]+=w
            by_op[(operators or {}).get(name,'unknown')]+=w
            chain.append({'task':name,'unit':u['row']['id'],'binding':u['binding']['id'],
                          'ticks':w,'actual_interval':[times[previous],times[terminal]]})
        elif kind=='resource':blockers[resource]+=1
        terminal=previous
    if sum(by_source.values())!=lower:raise ValueError('critical-chain attribution not conserved')
    # Upper-bound opportunity if all current non-arithmetic descriptor waits
    # could be improved is intentionally not inferred here.
    return {'passed':True,'schedule_audit':audit,'verified_makespan':plan['makespan'],
        'selected_order_relaxed_lower_bound':lower,'unexplained_or_rigid_wait_ticks':plan['makespan']-lower,
        'critical_chain_ticks_by_operator':dict(by_op),'critical_chain_resource_handoffs':dict(blockers),
        'critical_chain_top_tasks':[{'task':name,'ticks':ticks} for name,ticks in by_source.most_common(32)],
        'critical_chain':list(reversed(chain)),'execution_units':len(units),'event_vertices':len(times),
        'scope':'selected binding and resource-slot order only; split-stage relaxation, not global bound or executable improvement'}


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();ir=json.loads(a.ir.read_text());plan=json.loads(a.plan.read_text())
    result=profile(ir['tasks'],ir['hardware'],plan,operators={n['id']:n['op'] for n in ir.get('program',[])})
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('verified_makespan','selected_order_relaxed_lower_bound','critical_chain_ticks_by_operator')}))


if __name__=='__main__':main()
