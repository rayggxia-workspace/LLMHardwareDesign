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


def catalogue(tasks,covers,*,event_dependencies=None):
    by={t['id']:t for t in tasks}
    if len(by)!=len(tasks):raise ValueError('duplicate cover source task')
    hard={n:set(t.get('after',())) for n,t in by.items()}
    event_dependencies=event_dependencies or {}
    parents={n:hard[n]|{edge.task for edge in event_dependencies.get(n,())} for n in by}
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
        action['after']=set().union(*(hard[n] for n in members))-members
    return actions,parents,ancestors


def search(tasks,hardware,covers=(),*,width=16,ready_limit=4,wire_budget=None,backbone=None,rank_policy='shared_tail'):
    if (width is not None and (type(width)!=int or width<1) or
        ready_limit is not None and (type(ready_limit)!=int or ready_limit<1)):
        raise ValueError('positive cover frontier bounds required')
    if rank_policy not in ('shared_tail','hypergraph_completion','hypergraph_resources'):raise ValueError('unknown cover rank policy')
    covers=tuple(covers)
    model=None
    live_replay=False
    event_dependencies={}
    transport_counts={'transport_attempted':0,'transport_truncated':0}
    if 'event_model' in hardware:
        from event_execution import Model, Infeasible
        if rank_policy!='shared_tail' or hardware.get('window_calendar'):
            raise ValueError('event execution uses its own calendars and the shared-tail bound')
        if width==1 and covers:
            raise ValueError('strict event greedy requires singleton actions')
        model=Model(hardware,wire_budget=wire_budget)
        timing=hardware['event_model'].get('timing', 'calendar')
        if timing not in ('calendar', 'replay'):
            raise ValueError('unknown event timing model')
        live_replay=timing=='replay'
        if live_replay:
            from event_replay import ReplayDeadlock
            from event_replay_plan import Decision, retime
            from event_transport import draft, drafts
            transport_limit=hardware['event_model'].get('transport_limit',32)
            if transport_limit is not None and (type(transport_limit) is not int or transport_limit<1):
                raise ValueError('positive transport limit required')
    if any('event_after' in task for task in tasks):
        from event_execution import phase_edges
        event_dependencies={task['id']:phase_edges(task) for task in tasks}
        event_dependencies={name:edges for name,edges in event_dependencies.items() if edges}
        if event_dependencies and not live_replay:
            raise ValueError('phase edges require event replay')
    endpoints=set(event_dependencies)|{edge.task for edges in event_dependencies.values() for edge in edges}
    if any(len(a['covers'])>1 and endpoints.intersection(a['covers']) for a in covers):
        raise ValueError('multi-task cover has no mapping for its phase edge endpoints')
    # catalogue adds only derived fields to copies, never changes source IR.
    actions,parents,ancestors=catalogue(tasks,[dict(a) for a in covers],event_dependencies=event_dependencies)
    ids={t['id']:i for i,t in enumerate(tasks)};children={n:set() for n in ids}
    for n,ps in parents.items():
        for p in ps:children[p].add(n)
    indexed={n:[] for n in ids};by_action={a['id']:a for a in actions}
    masks={n:sum(1<<ids[p] for p in ps) for n,ps in parents.items()}
    phase_locations={}
    for name,edges in event_dependencies.items():
        for edge in edges:
            phase_locations.setdefault(edge.task,set()).add(edge.source)
            phase_locations.setdefault(name,set()).add(edge.target)
    users={}
    for a in actions:
        a['mask']=sum(1<<ids[n] for n in a['covers']);indexed[a['anchor']].append(a)
        for b in a['bindings']:
            if model:
                model.validate_binding(b)
                for location in phase_locations.get(a['covers'][0],()):
                    model.validate_phase(b,location)
                for stage in b['event_stages']:
                    for value in stage.get('inputs',{}).values():
                        users[value]=users.get(value,0)|a['mask']
            if (type(b['ticks'])!=int or b['ticks']<1 or
                len(set(b['resources']))!=len(b['resources']) or
                any(r not in hardware['resources'] for r in b['resources']) or
                any(n not in hardware['nets'] for n in b['nets']) or
                any(n<0 or n>hardware['sites'][s]['words'] for s,n in
                    b.get('scratch_by_site',{b['site']:b['scratch_words']}).items())):
                raise ValueError('invalid cover native binding')
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
    hard_parents={t['id']:set(t.get('after',())) for t in tasks}
    tail={}
    for n in reversed(ancestors):
        tail[n]=minimum[n]+max((tail[c] for c in children[n] if n in hard_parents[c]),default=0)
    initial=State(0,{}, {r:(0,)*c for r,c in hardware['resources'].items()},frozenset(),0,0,None,{},
                  frozenset(n for n in ids if not parents[n]),execution=model.initial if model else None)
    buckets={0:{}};calendar=calendar_resources(hardware);expanded=merged=pruned=seed_kept=0
    completion=None
    if rank_policy in ('hypergraph_completion','hypergraph_resources'):
        from cover_bounds import Completion
        completion=Completion(actions,hardware,ids,wire_budget=wire_budget,
                              resource_releases=rank_policy=='hypergraph_resources')
    def netcost(s):return sum(hardware['nets'][n]['cost'] for n in s.nets if n not in fixed)
    def key(s):return (s.done,tuple(sorted(s.frontier.items())),tuple(sorted(s.resources.items())),
        s.nets,tuple(sorted(s.cache.items())),tuple(sorted(s.windows.items())),
        s.execution.key() if s.execution is not None else None,
        tuple(decision.key() for decision in s.replay_decisions))
    def rank(s):
        bound=(completion.get(s) if completion else
            max([s.makespan]+[max((s.frontier[p] for p in hard_parents[n]),default=0)+tail[n] for n in s.ready]))
        return bound,s.makespan,s.traffic,netcost(s)
    def advance(s,a,b,policy,forced_choices=None):
        if s.done&a['mask'] or any(not s.done&(1<<ids[p]) for p in a['boundary']):return
        arrival=max((s.frontier[p] for p in a['after']),default=0)
        if model:
            protected={value for value,mask in users.items() if mask&~(s.done|a['mask'])}
            draft_state=s.execution.after(arrival) if live_replay else s.execution
            if live_replay and forced_choices is None:
                proposals=drafts(model,draft_state,b,arrival,protected,transport_limit,transport_counts)
            else:
                try:
                    if live_replay:
                        execution,events=draft(model,draft_state,b,arrival,protected,forced_choices)
                    else:
                        execution,events=model.expand(s.execution,b,arrival,protected)
                except Infeasible:
                    return
                proposals=((execution,events,forced_choices),)
            for execution,events,choices in proposals:
                result=event_successor(s,a,b,execution,events,choices)
                if result is not None:
                    yield result
        else:
            ev=evaluate(s,b,hardware,arrival,retention=policy,fixed=fixed,conflicts=conflicts,wire_budget=wire_budget)
            if ev['legal']:
                yield successor(s,a,b,ev)

    def event_successor(s,a,b,execution,events,choices):
        start=min(event['start'] for event in events)
        end=max(event['end'] for event in events)
        delta_reads=execution.read_bytes-s.execution.read_bytes
        delta_writes=execution.write_bytes-s.execution.write_bytes
        ev={'start':start,'end':end,'makespan':max(s.makespan,end),'nets':execution.nets,
            'resources':s.resources,'cache':s.cache,'traffic':delta_reads+delta_writes,
            'details':{'events':events,'external_read_bytes':delta_reads,
                       'external_write_bytes':delta_writes}}
        if live_replay:
            ev['details']['transport_choices']=list(choices)
        return successor(s,a,b,ev,execution)

    def successor(s,a,b,ev,execution=None):
        done=s.done|a['mask']
        enabled=set().union(*(children[n] for n in a['covers']))-set(a['covers'])
        ready=(s.ready-set(a['covers']))|{c for c in enabled if done&masks[c]==masks[c]}
        row={'id':a['id'],'covers':list(a['covers']),'binding':b['id'],'site':b['site'],
             'start':ev['start'],'end':ev['end']}
        if b.get('read_cache'):row['cache_hit']=ev['cache_hit']
        if ev['details']:row['evaluation']=ev['details']
        if calendar:row['resource_windows']=ev['resource_windows']
        decisions=s.replay_decisions
        trace=s.replay_trace
        history=History(s.history,row)
        frontier={**s.frontier,**dict.fromkeys(a['covers'],ev['end'])}
        if live_replay:
            decisions=(*decisions,Decision(row,frozenset(a['after']),event_dependencies.get(a['covers'][0],())))
            try:
                execution,rows,trace=retime(model,decisions,execution,trace)
            except ReplayDeadlock:
                return None
            history=None
            for scheduled in rows:
                history=History(history,scheduled)
                frontier.update(dict.fromkeys(scheduled['covers'],scheduled['end']))
            ev['makespan']=max(scheduled['end'] for scheduled in rows)
        frontier={n:at for n,at in frontier.items() if any(not done&(1<<ids[c]) for c in children[n])}
        if model and ready and not live_replay:
            cutoff=min(max((frontier[p] for p in parents[n]),default=0) for n in ready)
            execution=execution.after(cutoff)
        return State(done,frontier,ev['resources'],ev['nets'],ev['makespan'],s.traffic+ev['traffic'],
            history,ev['cache'],frozenset(ready),ev.get('windows',s.windows),execution,decisions,trace)
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
            choices=tuple(row['evaluation'].get('transport_choices',())) if live_replay else None
            s=next(advance(s,a,b,policy(b,row),choices),None)
            if s is None:raise ValueError('verified atomic backbone became illegal')
            if live_replay:
                proposed=s.history.row['evaluation']['events']
                expected=row['evaluation']['events']
                signature=lambda events: [(e['route'],e['value'],e['src'],e['dst'])
                                          for e in events if e['kind']=='move']
                if signature(proposed)!=signature(expected):
                    raise ValueError('backbone transport choice differs from verified plan')
            seeds[s.done.bit_count()]=s
    buckets[0][key(initial)]=initial;complete=[]
    for count in range(len(tasks)+1):
        pool=buckets.pop(count,{})
        if count in seeds:pool.setdefault(key(seeds[count]),seeds[count])
        candidates=pool.values()
        if model and count==len(tasks):
            candidates=[s for s in candidates if model.live_out <= (
                s.execution.backing.keys() | {copy.value for copy in s.execution.copies.values()})]
        ordered=sorted(candidates,key=rank);pruned+=max(0,len(ordered)-(width or len(ordered)))
        beam=ordered if width is None else ordered[:width]
        if count in seeds and all(key(s)!=key(seeds[count]) for s in beam):
            beam[-1]=seeds[count];seed_kept+=1
        if count==len(tasks):complete=beam;break
        for s in beam:
            roots=sorted(s.ready,key=lambda n:(-tail[n],n))
            if ready_limit is not None:roots=roots[:ready_limit]
            for n in roots:
                for a in indexed[n]:
                    if s.done&a['mask'] or any(not s.done&(1<<ids[p]) for p in a['boundary']):continue
                    for b in a['bindings']:
                        for policy in retention_actions(s,b):
                            expanded+=1
                            for ns in advance(s,a,b,policy):
                                k=key(ns);bucket=buckets.setdefault(ns.done.bit_count(),{});old=bucket.get(k)
                                if old is not None:
                                    merged+=1
                                    if (old.makespan,old.traffic)<=(ns.makespan,ns.traffic):continue
                                bucket[k]=ns
    timing_stats=({'timing':'replay','transport_limit':transport_limit,**transport_counts}
                  if live_replay else {})
    if not complete:return {'status':'no_plan_in_bounded_search','expanded':expanded,**timing_stats}
    best=min(complete,key=lambda s:(s.makespan,s.traffic,netcost(s)));rows=[];history=best.history
    while history is not None:rows.append(history.row);history=history.previous
    rows.reverse()
    traffic=({'external_read_bytes':best.execution.read_bytes,
              'external_write_bytes':best.execution.write_bytes} if model else {'external_words':best.traffic})
    return {'status':'planned','kind':'event-cover-frontier-v1' if model else 'convex-cover-frontier-v1',
        **timing_stats,
        'tasks':rows,'makespan':best.makespan,**traffic,'nets':sorted(best.nets),'wire_cost':netcost(best),'final_read_cache':best.cache,
        'expanded':expanded,'merged':merged,'pruned':pruned,'width':width,'ready_limit':ready_limit,
        'covered_original_tasks':len(tasks),'multi_task_decisions':sum(len(r['covers'])>1 for r in rows),
        'backbone_prefix_slots':seed_kept,'rank_policy':rank_policy,
        'completion_calls':completion.calls if completion else 0,
        'optimality':'bounded cover frontier; no global optimum claim'}
