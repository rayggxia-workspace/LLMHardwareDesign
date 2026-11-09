"""Bounded frontier DP for finite streaming kernels on the fixed leaf inventory.

Kernel bodies must separately prove finite private-S windows and acknowledged
external transfers. No whole tensor is presumed resident in S. Keeping bodies
as loops avoids expanding billions of native commands into search nodes.
"""
from dataclasses import dataclass,field
from transition import evaluate_transition, retention_actions
from static_wiring import completion_covers
from column_shards import leaf_rows
from service_bounds import optimistic_ticks


@dataclass(frozen=True)
class History:
    previous: object
    row: dict


@dataclass
class State:
    done: int
    frontier: dict
    resources: dict
    nets: frozenset
    makespan: int
    traffic: int
    history: object
    cache: dict
    ready: frozenset = frozenset()
    windows: dict = field(default_factory=dict)


def search(tasks,hardware,*,width=16,ready_limit=4,wire_budget=None,wire_lookahead=True,
           priority='minimum_tail',rank_policy='critical_bound',work_price_rounds=12,decision_order=None,
           backbone=None):
    if width<1 or ready_limit<1:raise ValueError('positive DP bounds required')
    from window_calendar import resources as window_resources,evaluate as window_evaluate
    calendar=window_resources(hardware)
    if backbone is not None:
        if width<2:raise ValueError('incumbent backbone needs at least two beam slots')
        if decision_order is not None:raise ValueError('choose supplied order or incumbent backbone')
        from verify_loop_dp import verify
        verify(tasks,hardware,backbone,wire_budget=wire_budget)
    if priority not in ('minimum_tail','heft') or rank_policy not in ('critical_bound','earliest_finish','net_conditioned_tail','net_resource_tail','net_work_price','net_future_resource_tail'):
        raise ValueError('unknown loop scheduling policy')
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
    if decision_order is not None and (len(decision_order)!=len(ids) or set(decision_order)!=set(ids)):
        raise ValueError('decision order must cover every task once')
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
    tail={};priority_tail={};pending=set(ids)
    while pending:
        ready=[n for n in pending if all(c in tail for c in children[n])]
        if not ready:raise ValueError('cycle in streaming graph')
        for n in ready:
            tail[n]=min(optimistic_ticks(b) for b in tasks[ids[n]]['bindings'])+max((tail[c] for c in children[n]),default=0)
            options=tasks[ids[n]]['bindings']
            mean_cold=(sum(optimistic_ticks(b,warm=False) for b in options)+len(options)-1)//len(options)
            priority_tail[n]=(mean_cold if priority=='heft' else min(optimistic_ticks(b) for b in options))+max(
                (priority_tail[c] for c in children[n]),default=0)
            pending.remove(n)
    initial=State(0,{}, {r:(0,)*c for r,c in hardware['resources'].items()},frozenset(),0,0,None,{},
                  frozenset(n for n in ids if not parents[n]))
    completions=completion_covers(tasks,hardware,wire_budget=wire_budget) if wire_lookahead else None
    conditional=None
    if rank_policy in ('net_conditioned_tail','net_resource_tail','net_work_price','net_future_resource_tail'):
        from net_tail import ConditionalTail
        conditional=ConditionalTail(tasks,hardware,children,tuple(tail),fixed=fixed,
            conflicts=conflicts,wire_budget=wire_budget,completions=completions)
    work_price=None
    if rank_policy=='net_work_price':
        from work_price import WorkPriceBound
        work_price=WorkPriceBound(conditional,tasks,hardware,rounds=work_price_rounds)
    future=None
    if rank_policy=='net_future_resource_tail':
        from future_resource_tail import FutureResourceTail
        future=FutureResourceTail(conditional,tasks,hardware)
    beam=[initial];seed_state=initial;seed_rows=backbone['tasks'] if backbone is not None else None
    expanded=0;pruned=0;merged=0;static_rejections=0;completion_rejections=0;seed_kept=0
    def ready_for(state):
        # A transition can only enable children of its selected task. The
        # ready set is determined by done, so it does not enlarge the DP key.
        # Avoid rescanning thousands of unrelated primitives per state.
        return [tasks[ids[n]] for n in state.ready]
    def netcost(nets):return sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    def state_key(state):
        return (state.done,tuple(sorted(state.frontier.items())),tuple(sorted(state.resources.items())),
                tuple(sorted(state.nets)),tuple(sorted(state.cache.items())),tuple(sorted(state.windows.items())))
    def advance(s,task,b,retention):
        name=task['id'];data_ready=max((s.frontier[p] for p in parents[name]),default=0)
        ev=window_evaluate(s,b,hardware,data_ready,retention=retention,
            fixed=fixed,conflicts=conflicts,wire_budget=wire_budget,wire_completions=completions)
        if not ev['legal']:return None,ev['reason']
        if type(ev['start'])!=int or type(ev['end'])!=int:
            raise TypeError('noninteger service time '+repr((name,b['id'],ev['start'],ev['end'])))
        done=s.done|(1<<ids[name]);frontier=s.frontier.copy();frontier[name]=ev['end']
        frontier={n:at for n,at in frontier.items() if any(not done&(1<<ids[c]) for c in children[n])}
        row={'id':name,'binding':b['id'],'start':ev['start'],'end':ev['end'],'site':b['site']}
        if b.get('read_cache'):row['cache_hit']=ev['cache_hit']
        if ev['details']:row['evaluation']=ev['details']
        if calendar:row['resource_windows']=ev['resource_windows']
        enabled=frozenset(c for c in children[name] if done&masks[c]==masks[c])
        return State(done,frontier,ev['resources'],ev['nets'],ev['makespan'],s.traffic+ev['traffic'],
            History(s.history,row),ev['cache'],(s.ready-{name})|enabled,ev.get('windows',s.windows)),None
    def replay_policy(binding,row):
        if 'parallel_shards' in binding:
            return tuple(replay_policy(c['binding'],r) for c,r in zip(
                binding['parallel_shards']['children'],row['evaluation']['services']))
        if binding.get('dot_tile'):return 'invalidate'
        return row.get('evaluation',{}).get('retention','legacy')
    def rank(s):
        if rank_policy=='earliest_finish':
            return (s.history.row['end'] if s.history else 0),s.makespan,s.traffic,netcost(s.nets)
        ready=ready_for(s)
        bounds=[s.makespan]
        state_tail=conditional.get(s.nets) if conditional is not None else tail
        for task in ready:
            arrivals=[s.frontier[p] for p in parents[task['id']]]
            value=state_tail[task['id']]
            if value is None:return float('inf'),s.makespan,s.traffic,netcost(s.nets)
            if any(type(at)!=int for at in arrivals) or type(value)!=int:
                raise TypeError('noninteger frontier/tail '+repr((task['id'],arrivals,value)))
            if rank_policy in ('net_resource_tail','net_work_price','net_future_resource_tail'):
                finish=conditional.ready_finish(task['id'],s.nets,s.resources,max(arrivals,default=0),windows=s.windows)
                if finish is None:return float('inf'),s.makespan,s.traffic,netcost(s.nets)
                bounds.append(finish+max((state_tail[c] for c in children[task['id']]),default=0))
            else:bounds.append(max(arrivals,default=0)+value)
        if work_price is not None:
            work_bound=work_price.get(s)
            if work_bound is None:return float('inf'),s.makespan,s.traffic,netcost(s.nets)
            bounds.append(work_bound)
        if future is not None:
            value=future.get(s,max(bounds))
            if value is None:return float('inf'),s.makespan,s.traffic,netcost(s.nets)
            bounds.append(value)
        bound=max(bounds)
        return bound,s.makespan,s.traffic,netcost(s.nets)
    for depth in range(len(tasks)):
        candidates={}
        for s in beam:
            ready=ready_for(s)
            ready.sort(key=lambda t:(-priority_tail[t['id']],t['id']))
            if decision_order is not None:
                ready=[t for t in ready if t['id']==decision_order[depth]]
                if not ready:raise ValueError('decision order violates dependencies')
            for task in ready[:ready_limit]:
                for b in task['bindings']:
                    for retention in retention_actions(s, b):
                        expanded+=1
                        state,reason=advance(s,task,b,retention)
                        if state is None:
                            static_rejections+=reason=='static_conflict'
                            completion_rejections+=reason=='wire_budget_completion'
                            continue
                        key=state_key(state)
                        previous=candidates.get(key)
                        if previous is not None:
                            merged+=1
                            if (previous.makespan,previous.traffic)<=(state.makespan,state.traffic):continue
                        candidates[key]=state
        if seed_rows is not None:
            row=seed_rows[depth];task=tasks[ids[row['id']]]
            if task['id'] not in seed_state.ready:raise ValueError('backbone decision precedes dependency')
            b=next(b for b in task['bindings'] if b['id']==row['binding'])
            seed_state,reason=advance(seed_state,task,b,replay_policy(b,row))
            if seed_state is None:raise ValueError('verified backbone replay became illegal '+reason)
            candidates.setdefault(state_key(seed_state),seed_state)
        ordered=sorted(candidates.values(),key=rank);pruned+=max(0,len(ordered)-width);beam=ordered[:width]
        if seed_rows is not None and depth+1<len(tasks) and all(state_key(s)!=state_key(seed_state) for s in beam):
            beam[-1]=seed_state;seed_kept+=1
        if not beam:return {'status':'no_plan_in_bounded_search','depth':depth,'expanded':expanded,
                            'rejected_static_conflicts':static_rejections,
                            'rejected_wire_completions':completion_rejections}
    best=min(beam,key=lambda s:(s.makespan,s.traffic,netcost(s.nets)))
    # Share immutable history prefixes instead of copying an O(depth) tuple
    # for every candidate. Materialize only the chosen complete schedule.
    rows=[];history=best.history
    while history is not None:
        rows.append(history.row);history=history.previous
    rows.reverse()
    return {'status':'planned','tasks':rows,'makespan':best.makespan,'external_words':best.traffic,
        'nets':sorted(best.nets),'wire_cost':netcost(best.nets),'width':width,'ready_limit':ready_limit,
        'expanded':expanded,'merged':merged,'pruned':pruned,'rejected_static_conflicts':static_rejections,
        'rejected_wire_completions':completion_rejections,
        'wire_completion_covers':len(completions) if completions is not None else None,
        'read_cache_hits':sum(s.get('cache_hit',False) for r in rows for s in leaf_rows(r)),
        'read_cache_calls':sum('cache_hit' in s for r in rows for s in leaf_rows(r)),
        'final_read_cache':best.cache,
        'scheduling_policy':{'priority':priority,'rank':rank_policy},
        'decision_order':'supplied-topological-order' if decision_order is not None else 'frontier-ready-search',
        'backbone':{'enabled':seed_rows is not None,'forced_prefix_slots':seed_kept,
            'replayed_prefixes':len(seed_rows) if seed_rows is not None else 0,
            'slot_budget':width,'scope':'one incumbent prefix inside the same beam budget; actual state/cost replay, no frozen timestamps'},
        'conditional_tail_statistics':conditional.statistics() if conditional is not None else None,
        'work_price_statistics':work_price.statistics() if work_price is not None else None,
        **({'future_resource_tail_statistics':future.statistics()} if future is not None else {}),
        'calendar_kind':'fixed-offset-calendar-v1' if calendar else 'append-only',
        'optimality':'bounded frontier DP; append-only primary calendars and explicit optional auxiliary windows; no global optimality guarantee'}


def optimize(tasks,hardware,*,incumbents=(),**kwargs):
    baseline=search(tasks,hardware,**{**kwargs,'width':1})
    proposed=search(tasks,hardware,**kwargs)
    choices=[(source,p) for source,p in (('greedy',baseline),('frontier',proposed)) if p['status']=='planned']
    if incumbents:
        from verify_loop_dp import verify
        for p in incumbents:
            verify(tasks,hardware,p,wire_budget=kwargs.get('wire_budget'))
            choices.append(('incumbent',p))
    if not choices:return {'status':'no_plan_in_bounded_search','baseline':baseline,'search':proposed}
    source,best=min(choices,key=lambda pair:(pair[1]['makespan'],pair[1]['external_words'],pair[1]['wire_cost']))
    best=best.copy();best['selected_source']=source;best['incumbent_count']=len(incumbents)
    best['baseline']=baseline;best['search_statistics']={k:proposed.get(k) for k in (
        'status','expanded','merged','pruned','width','rejected_static_conflicts','rejected_wire_completions','wire_completion_covers')}
    return best
