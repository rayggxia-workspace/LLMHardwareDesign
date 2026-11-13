"""One frontier over native tasks and alternative convex multi-task services.

The done mask always names original tasks. Buckets advance by the number of
covered tasks, not the number of decisions: a 4-task service and four atomic
services therefore meet in the same bucket. All original bindings survive.
Bounded beams are heuristic; width=None/ready_limit=None enumerate small DAGs.
"""
from loop_dp import History,State
from service_bounds import optimistic_ticks
from transition import retention_actions
from window_calendar import evaluate,resources as calendar_resources


def catalogue(tasks,covers):
    by={t['id']:t for t in tasks}
    if len(by)!=len(tasks):raise ValueError('duplicate cover source task')
    parents={n:set(t.get('after',())) for n,t in by.items()}
    if any(not ps<=by.keys() for ps in parents.values()):raise ValueError('unknown cover dependency')
    ancestors={};pending=set(by)
    while pending:
        ready=sorted(n for n in pending if parents[n]<=ancestors.keys())
        if not ready:raise ValueError('cycle in cover source graph')
        for n in ready:
            ancestors[n]=parents[n]|set().union(*(ancestors[p] for p in parents[n]))
            pending.remove(n)
    actions=[{'id':n,'covers':[n],'bindings':t['bindings']} for n,t in by.items()]
    actions+=covers
    names=set()
    for action in actions:
        name=action['id'];group=action['covers'];members=set(group)
        if name in names or not group or len(group)!=len(members) or not members<=by.keys():
            raise ValueError('ambiguous cover action identity/membership')
        names.add(name)
        if not action['bindings'] or len({b['id'] for b in action['bindings']})!=len(action['bindings']):
            raise ValueError('ambiguous/empty cover binding pool')
        outside=set().union(*(parents[n] for n in members))-members
        if any(ancestors[p]&members for p in outside):raise ValueError('nonconvex task cover')
        roots={n for n in members if not parents[n]&members}
        action['boundary']=outside;action['anchor']=min(roots)
    return actions,parents,ancestors


def search(tasks,hardware,covers=(),*,width=16,ready_limit=4,wire_budget=None,backbone=None,
           rank_policy='shared_tail',route_admission=None):
    if (width is not None and (type(width)!=int or width<1) or
        ready_limit is not None and (type(ready_limit)!=int or ready_limit<1)):
        raise ValueError('positive cover frontier bounds required')
    if rank_policy not in ('shared_tail','hypergraph_completion','hypergraph_resources'):raise ValueError('unknown cover rank policy')
    # catalogue adds only derived fields to copies, never changes source IR.
    actions,parents,ancestors=catalogue(tasks,[dict(a) for a in covers])
    model=None
    if 'event_model' in hardware:
        from event_execution import Model
        if rank_policy!='shared_tail' or hardware.get('window_calendar'):
            raise ValueError('event execution uses its own calendars and the shared-tail bound')
        model=Model(hardware,wire_budget=wire_budget,route_admission=route_admission)
    ids={t['id']:i for i,t in enumerate(tasks)};children={n:set() for n in ids}
    for n,ps in parents.items():
        for p in ps:children[p].add(n)
    indexed={n:[] for n in ids};by_action={a['id']:a for a in actions}
    masks={n:sum(1<<ids[p] for p in ps) for n,ps in parents.items()}
    users={}
    required = {}
    for a in actions:
        a['mask']=sum(1<<ids[n] for n in a['covers']);indexed[a['anchor']].append(a)
        for b in a['bindings']:
            if model:
                model.validate_binding(b)
                nets = set(b['nets'])
                for stage in b['event_stages']:
                    nets.update(model.services[stage['service']].get('nets', ()))
                    for value in stage.get('inputs',{}).values():
                        users[value]=users.get(value,0)|a['mask']
                if not any(stage['service'] in model.unqualified_services for stage in b['event_stages']):
                    for node in a['covers']:
                        required[node] = required.get(node, nets) & nets
            if (type(b['ticks'])!=int or b['ticks']<1 or
                len(set(b['resources']))!=len(b['resources']) or
                any(r not in hardware['resources'] for r in b['resources']) or
                any(n not in hardware['nets'] for n in b['nets']) or
                any(n<0 or n>hardware['sites'][s]['words'] for s,n in
                    b.get('scratch_by_site',{b['site']:b['scratch_words']}).items())):
                raise ValueError('invalid cover native binding')
    if model:
        model.required_nets = frozenset().union(*required.values())
    fixed=frozenset(n for n,m in hardware['nets'].items() if m.get('fixed'))
    conflicts=[]
    for pair in hardware.get('incompatible_nets',()):
        if len(pair)!=2 or pair[0]==pair[1] or any(n not in hardware['nets'] for n in pair):
            raise ValueError('invalid cover static conflict')
        conflicts.append(frozenset(pair))
    if any(p<=fixed for p in conflicts):raise ValueError('incompatible fixed static connections')
    # Relax each cover's duration equally onto its original nodes. Any path
    # uses at most len(cover) shares. Unlike an atomic-only tail, this does not
    # charge both the fused service and the work it replaced.
    minimum={n:min(optimistic_ticks(b) for b in tasks[ids[n]]['bindings']) for n in ids}
    for a in actions:
        share=min(optimistic_ticks(b) for b in a['bindings'])//len(a['covers'])
        for n in a['covers']:minimum[n]=min(minimum[n],share)
    tail={}
    for n in reversed(ancestors):tail[n]=minimum[n]+max((tail[c] for c in children[n]),default=0)
    initial=State(0,{}, {r:(0,)*c for r,c in hardware['resources'].items()},frozenset(),0,0,None,{},
                  frozenset(n for n in ids if not parents[n]),execution=model.initial if model else None)
    buckets={0:{}};calendar=calendar_resources(hardware);expanded=merged=pruned=seed_kept=0
    completion=None
    if rank_policy in ('hypergraph_completion','hypergraph_resources'):
        from cover_bounds import Completion
        completion=Completion(actions,hardware,ids,wire_budget=wire_budget,
                              resource_releases=rank_policy=='hypergraph_resources')
    def netcost(s):
        if model:
            return model.wire_cost(s.nets)
        return sum(hardware['nets'][n]['cost'] for n in s.nets if n not in fixed)
    def key(s):return (s.done,tuple(sorted(s.frontier.items())),tuple(sorted(s.resources.items())),
        s.nets,tuple(sorted(s.cache.items())),tuple(sorted(s.windows.items())),
        s.execution.key() if s.execution is not None else None)
    def rank(s):
        bound=(completion.get(s) if completion else
            max([s.makespan]+[max((s.frontier[p] for p in parents[n]),default=0)+tail[n] for n in s.ready]))
        return bound,s.makespan,s.traffic,netcost(s)
    def advance(s,a,b,policy):
        if s.done&a['mask'] or any(not s.done&(1<<ids[p]) for p in a['boundary']):
            return
        arrival=max((s.frontier[p] for p in a['boundary']),default=0)
        if model:
            protected={value for value,mask in users.items() if mask&~(s.done|a['mask'])}
            for execution,events in model.expand_choices(s.execution,b,arrival,protected):
                start=min(event['start'] for event in events)
                end=max(event['end'] for event in events)
                delta_reads=execution.read_bytes-s.execution.read_bytes
                delta_writes=execution.write_bytes-s.execution.write_bytes
                ev={'start':start,'end':end,'makespan':max(s.makespan,end),'nets':execution.nets,
                    'resources':s.resources,'cache':s.cache,'traffic':delta_reads+delta_writes,
                    'details':{'events':events,'external_read_bytes':delta_reads,
                               'external_write_bytes':delta_writes}}
                yield commit(s,a,b,ev,execution)
        else:
            ev=evaluate(s,b,hardware,arrival,retention=policy,fixed=fixed,conflicts=conflicts,wire_budget=wire_budget)
            if ev['legal']:
                yield commit(s,a,b,ev,None)

    def commit(s,a,b,ev,execution):
        done=s.done|a['mask'];frontier={**s.frontier,**dict.fromkeys(a['covers'],ev['end'])}
        frontier={n:at for n,at in frontier.items() if any(not done&(1<<ids[c]) for c in children[n])}
        enabled=set().union(*(children[n] for n in a['covers']))-set(a['covers'])
        ready=(s.ready-set(a['covers']))|{c for c in enabled if done&masks[c]==masks[c]}
        if model and ready:
            cutoff=min(max((frontier[p] for p in parents[n]),default=0) for n in ready)
            execution=execution.after(cutoff)
        row={'id':a['id'],'covers':list(a['covers']),'binding':b['id'],'site':b['site'],
             'start':ev['start'],'end':ev['end']}
        if not model and b.get('read_cache'):row['cache_hit']=ev['cache_hit']
        if ev['details']:row['evaluation']=ev['details']
        if calendar:row['resource_windows']=ev['resource_windows']
        return State(done,frontier,ev['resources'],ev['nets'],ev['makespan'],s.traffic+ev['traffic'],
            History(s.history,row),ev['cache'],frozenset(ready),ev.get('windows',s.windows),execution)
    seeds={}
    if backbone is not None:
        if backbone.get('kind') in ('convex-cover-frontier-v1','event-cover-frontier-v1'):
            from verify_cover_frontier import verify
            verify(tasks,hardware,covers,backbone,wire_budget=wire_budget)
        else:
            from verify_loop_dp import verify
            verify(tasks,hardware,backbone,wire_budget=wire_budget)
        if width is not None and width<2:raise ValueError('cover backbone requires two beam slots')
        # Replay the original row policies with current state, never copy its
        # timestamps or assume its cache survives a different predecessor.
        s=initial
        def policy(b,row):
            if 'parallel_shards' in b:return tuple(policy(c['binding'],r) for c,r in zip(
                b['parallel_shards']['children'],row['evaluation']['services']))
            if b.get('dot_tile') or b.get('resident_region'):return 'invalidate'
            return row.get('evaluation',{}).get('retention','legacy')
        for row in backbone['tasks']:
            a=by_action[row['id']];b=next(b for b in a['bindings'] if b['id']==row['binding'])
            alternatives = advance(s,a,b,'event' if model else policy(b,row))
            if model:
                alternatives = (state for state in alternatives
                                if state.history.row['evaluation']['events'] == row['evaluation']['events'])
            s=next(alternatives,None)
            if s is None:raise ValueError('verified atomic backbone became illegal')
            seeds[s.done.bit_count()]=s
    def successors(s):
        nonlocal expanded
        roots=sorted(s.ready,key=lambda n:(-tail[n],n))
        if ready_limit is not None:
            roots=roots[:ready_limit]
        for n in roots:
            for a in indexed[n]:
                if s.done&a['mask'] or any(not s.done&(1<<ids[p]) for p in a['boundary']):
                    continue
                for binding in a['bindings']:
                    policies = ('event',) if model else retention_actions(s,binding)
                    for policy in policies:
                        expanded += 1
                        yield from advance(s,a,binding,policy)

    def retain(pool,state):
        nonlocal merged
        k=key(state)
        previous=pool.setdefault(k,[])
        if not model:
            if previous:
                merged += 1
                old=previous[0]
                if (old.makespan,old.traffic)<=(state.makespan,state.traffic):
                    return
            previous[:]=[state]
            return
        # Both objectives must improve. An existing time lead can disappear
        # when a later action dominates the final makespan.
        if any(old.makespan<=state.makespan and old.traffic<=state.traffic for old in previous):
            merged += 1
            return
        remaining=[old for old in previous
                   if not (state.makespan<=old.makespan and state.traffic<=old.traffic)]
        merged += len(previous)-len(remaining)
        previous[:]=[*remaining,state]

    def valid_output(s):
        return not model or model.live_out <= (
            s.execution.backing.keys() | {copy.value for copy in s.execution.copies.values()})

    complete=[]
    if model and width==1:
        s=initial
        while s is not None and s.done.bit_count()<len(tasks):
            s=min((candidate for candidate in successors(s)
                   if candidate.done.bit_count()<len(tasks) or valid_output(candidate)),
                  key=rank,default=None)
        if s is not None and valid_output(s):
            complete=[s]
    else:
        retain(buckets[0],initial)
        for count in range(len(tasks)+1):
            pool=buckets.pop(count,{})
            seed=seeds.get(count)
            if seed is not None:
                retain(pool,seed)
            candidates=(s for group in pool.values() for s in group
                        if count!=len(tasks) or valid_output(s))
            ordered=sorted(candidates,key=rank)
            pruned+=max(0,len(ordered)-(width or len(ordered)))
            beam=ordered if width is None else ordered[:width]
            if seed is not None and all((key(s),s.makespan,s.traffic)!=(key(seed),seed.makespan,seed.traffic)
                                        for s in beam):
                if beam:
                    beam[-1]=seed
                elif count!=len(tasks) or valid_output(seed):
                    beam=[seed]
                seed_kept+=1
            if count==len(tasks):
                complete=beam
                break
            for s in beam:
                for candidate in successors(s):
                    retain(buckets.setdefault(candidate.done.bit_count(),{}),candidate)
    if not complete:return {'status':'no_plan_in_bounded_search','expanded':expanded}
    best=min(complete,key=lambda s:(s.makespan,s.traffic,netcost(s)));rows=[];history=best.history
    while history is not None:rows.append(history.row);history=history.previous
    rows.reverse()
    traffic=({'external_read_bytes':best.execution.read_bytes,
              'external_write_bytes':best.execution.write_bytes} if model else {'external_words':best.traffic})
    return {'status':'planned','kind':'event-cover-frontier-v1' if model else 'convex-cover-frontier-v1',
        'tasks':rows,'makespan':best.makespan,**traffic,'nets':sorted(best.nets),'wire_cost':netcost(best),'final_read_cache':best.cache,
        'expanded':expanded,'merged':merged,'pruned':pruned,'width':width,'ready_limit':ready_limit,
        'covered_original_tasks':len(tasks),'multi_task_decisions':sum(len(r['covers'])>1 for r in rows),
        'backbone_prefix_slots':seed_kept,'rank_policy':rank_policy,
        'completion_calls':completion.calls if completion else 0,
        'optimality':'bounded cover frontier; no global optimum claim'}
