"""Bounded frontier DP for finite streaming kernels on the fixed leaf inventory.

Kernel bodies must separately prove finite private-S windows and acknowledged
external transfers. No whole tensor is presumed resident in S. Keeping bodies
as loops avoids expanding billions of native commands into search nodes.
"""
from dataclasses import dataclass
from transition import evaluate_transition, retention_actions


@dataclass
class State:
    done: int
    frontier: dict
    resources: dict
    nets: frozenset
    makespan: int
    traffic: int
    history: tuple
    cache: dict


def search(tasks,hardware,*,width=16,ready_limit=4,wire_budget=None):
    if width<1 or ready_limit<1:raise ValueError('positive DP bounds required')
    # These are physical alternatives, not time-shared resources. Preserve
    # the entire product's selected union even after its last user finishes.
    fixed=frozenset(n for n,meta in hardware['nets'].items() if meta.get('fixed'))
    conflicts=[]
    for pair in hardware.get('incompatible_nets',[]):
        if (not isinstance(pair,(list,tuple)) or len(pair)!=2 or
            any(not isinstance(n,str) or n not in hardware['nets'] for n in pair) or pair[0]==pair[1]):
            raise ValueError('invalid incompatible_nets pair')
        conflicts.append(frozenset(pair))
    if any(pair<=fixed for pair in conflicts):raise ValueError('incompatible fixed static connections')
    ids={t['id']:i for i,t in enumerate(tasks)}
    if len(ids)!=len(tasks):raise ValueError('duplicate loop task')
    children={t['id']:[] for t in tasks};parents={};masks={}
    for t in tasks:
        ps=set(t.get('after',[]))
        if not ps<=ids.keys():raise ValueError('unknown loop dependency')
        parents[t['id']]=ps;masks[t['id']]=sum(1<<ids[p] for p in ps)
        for p in ps:children[p].append(t['id'])
        if not t['bindings']:raise ValueError('kernel has no native binding')
        for b in t['bindings']:
            if b['ticks']<1 or b.get('warm_ticks',b['ticks'])<1 or len(set(b['resources']))!=len(b['resources']):raise ValueError('invalid loop binding')
            if any(r not in hardware['resources'] for r in b['resources']):raise ValueError('unknown loop resource')
            if any(n not in hardware['nets'] for n in b['nets']):raise ValueError('unknown loop net')
            scratch=b.get('scratch_by_site',{b['site']:b['scratch_words']})
            if any(n>hardware['sites'][site]['words'] for site,n in scratch.items()):raise ValueError('kernel scratch exceeds private S')
    # Critical-path lower bound ignores contention; it is a ranking heuristic,
    # never a proof of optimality after beam/ready pruning.
    tail={};pending=set(ids)
    while pending:
        ready=[n for n in pending if all(c in tail for c in children[n])]
        if not ready:raise ValueError('cycle in streaming graph')
        for n in ready:
            tail[n]=min(b.get('warm_ticks',b['ticks']) for b in tasks[ids[n]]['bindings'])+max((tail[c] for c in children[n]),default=0)
            pending.remove(n)
    initial=State(0,{}, {r:(0,)*c for r,c in hardware['resources'].items()},frozenset(),0,0,(),{})
    beam=[initial];expanded=0;pruned=0;merged=0;static_rejections=0
    ready_cache={}
    def ready_for(done):
        # Candidate bindings of the same next task share this set. Recompute
        # once per done mask, rather than scanning the model for every tile.
        if done not in ready_cache:
            ready_cache[done]=[t for t in tasks if not done&(1<<ids[t['id']]) and done&masks[t['id']]==masks[t['id']]]
        return ready_cache[done]
    def netcost(nets):return sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    def rank(s):
        ready=ready_for(s.done)
        bound=max([s.makespan]+[max((s.frontier[p] for p in parents[t['id']]),default=0)+tail[t['id']] for t in ready])
        return bound,s.makespan,s.traffic,netcost(s.nets)
    for depth in range(len(tasks)):
        ready_cache.clear()
        candidates={}
        for s in beam:
            ready=list(ready_for(s.done))
            ready.sort(key=lambda t:(-tail[t['id']],t['id']))
            for task in ready[:ready_limit]:
                name=task['id']
                data_ready=max((s.frontier[p] for p in parents[name]),default=0)
                for b in task['bindings']:
                    for retention in retention_actions(s, b):
                        expanded+=1
                        ev=evaluate_transition(s,b,hardware,data_ready,retention=retention,
                            fixed=fixed,conflicts=conflicts,wire_budget=wire_budget)
                        if not ev['legal']:
                            static_rejections+=ev['reason']=='static_conflict'
                            continue
                        done=s.done|(1<<ids[name]);frontier=s.frontier.copy();frontier[name]=ev['end']
                        frontier={n:at for n,at in frontier.items() if any(not done&(1<<ids[c]) for c in children[n])}
                        row={'id':name,'binding':b['id'],'start':ev['start'],'end':ev['end'],'site':b['site']}
                        if b.get('read_cache'):row['cache_hit']=ev['cache_hit']
                        if ev['details']:row['evaluation']=ev['details']
                        state=State(done,frontier,ev['resources'],ev['nets'],ev['makespan'],
                            s.traffic+ev['traffic'],s.history+(row,),ev['cache'])
                        key=(done,tuple(sorted(frontier.items())),tuple(sorted(state.resources.items())),tuple(sorted(state.nets)),tuple(sorted(state.cache.items())))
                        previous=candidates.get(key)
                        if previous is not None:
                            merged+=1
                            if (previous.makespan,previous.traffic)<=(state.makespan,state.traffic):continue
                        candidates[key]=state
        ordered=sorted(candidates.values(),key=rank);pruned+=max(0,len(ordered)-width);beam=ordered[:width]
        if not beam:return {'status':'no_plan_in_bounded_search','depth':depth,'expanded':expanded,
                            'rejected_static_conflicts':static_rejections}
    best=min(beam,key=lambda s:(s.makespan,s.traffic,netcost(s.nets)))
    return {'status':'planned','tasks':list(best.history),'makespan':best.makespan,'external_words':best.traffic,
        'nets':sorted(best.nets),'wire_cost':netcost(best.nets),'width':width,'ready_limit':ready_limit,
        'expanded':expanded,'merged':merged,'pruned':pruned,'rejected_static_conflicts':static_rejections,
        'read_cache_hits':sum(r.get('cache_hit',False) for r in best.history),
        'read_cache_calls':sum('cache_hit' in r for r in best.history),
        'final_read_cache':best.cache,
        'optimality':'bounded frontier DP with append-only resource calendars; no global optimality guarantee'}


def optimize(tasks,hardware,**kwargs):
    baseline=search(tasks,hardware,**{**kwargs,'width':1})
    proposed=search(tasks,hardware,**kwargs)
    choices=[p for p in (baseline,proposed) if p['status']=='planned']
    if not choices:return {'status':'no_plan_in_bounded_search','baseline':baseline,'search':proposed}
    best=min(choices,key=lambda p:(p['makespan'],p['external_words'],p['wire_cost'])).copy()
    best['baseline']=baseline;best['search_statistics']={k:proposed.get(k) for k in ('expanded','merged','pruned','width','rejected_static_conflicts')}
    return best
