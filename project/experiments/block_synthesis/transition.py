"""Pure state-dependent evaluation shared by greedy and bounded frontier DP.

No input state or binding is mutated. Existing serial command/LOAD/STORE
semantics are retained; no transfer/computation overlap is assumed.
"""
from static_wiring import can_complete
from itertools import product
from types import SimpleNamespace


def retention_actions(state, binding):
    if 'parallel_shards' in binding:
        return tuple(product(*(retention_actions(state,c['binding'])
                               for c in binding['parallel_shards']['children'])))
    if binding.get('dot_tile') or binding.get('resident_region'):
        return ('invalidate',)
    c = binding.get('read_cache')
    if not c or c.get('cost_model') != 'dot-prefix-state-v2':
        return ('legacy',)
    old = state.cache.get(c['site'])
    actions = ['preserve']
    if c['stripe'] or old:
        actions.append('discard')
    if old and old[0] == c['tag'] and old[1] > c['stripe'] and c['stripe']:
        actions.append('shrink')
    return tuple(actions)


def evaluate_transition(state, binding, hardware, data_ready, *, retention='legacy',
                        fixed=frozenset(), conflicts=(), wire_budget=None, wire_completions=None):
    nets = state.nets | frozenset(binding['nets'])
    if any(pair <= nets | fixed for pair in conflicts):
        return {'legal': False, 'reason': 'static_conflict'}
    wire_cost=0
    for n in nets:
        try:meta=hardware['nets'][n]
        except KeyError as error:
            raise ValueError('unknown frontier static net '+repr({'net':n,'binding':binding['id'],
                'declared_nets':list(hardware['nets']),'selected_nets':sorted(nets)})) from error
        if not meta.get('fixed'):wire_cost+=meta['cost']
    if wire_budget is not None and wire_cost > wire_budget:
        return {'legal': False, 'reason': 'wire_budget'}
    if wire_budget is not None and not can_complete(nets,hardware,wire_completions,wire_budget,
                                                   fixed=fixed,conflicts=conflicts):
        return {'legal':False,'reason':'wire_budget_completion'}
    if 'parallel_shards' in binding:
        if 'phase_execution' in binding:
            if binding['phase_execution'].get('kind')=='native-tile-compound-fcfs-v1':
                from tile_phases import evaluate
            else:
                from phased_compounds import evaluate
            def leaf(current,b,h,ready,retention):
                return evaluate_transition(current,b,h,ready,retention=retention,
                    fixed=fixed,conflicts=conflicts)
            return evaluate(state,binding,hardware,data_ready,retention,leaf)
        spec=binding['parallel_shards'];children=spec['children']
        if 'frontier_partition' in binding:
            from dynamic_columns import resolve
            children=resolve(binding,state,data_ready)
        if not isinstance(retention,tuple) or len(retention)!=len(children):
            return {'legal':False,'reason':'retention_policy'}
        current=SimpleNamespace(resources=state.resources,cache=state.cache,nets=state.nets,
                                makespan=state.makespan)
        services=[];traffic=0
        for i,(child,policy) in enumerate(zip(children,retention)):
            b=child['binding']
            ev=evaluate_transition(current,b,hardware,data_ready,retention=policy,
                fixed=fixed,conflicts=conflicts,wire_budget=wire_budget,wire_completions=wire_completions)
            if not ev['legal']:return ev
            row={'id':spec['primitive']+'#columns-'+str(i),'binding':b['id'],
                 'site':b['site'],'start':ev['start'],'end':ev['end']}
            if b.get('read_cache'):row['cache_hit']=ev['cache_hit']
            if ev['details']:row['evaluation']=ev['details']
            services.append(row);traffic+=ev['traffic']
            current=SimpleNamespace(resources=ev['resources'],cache=ev['cache'],
                                    nets=ev['nets'],makespan=ev['makespan'])
        details={'cost_model':'dot-column-shards-v1','services':services,
                 'delta_makespan':current.makespan-state.makespan}
        if 'frontier_partition' in binding:details['resolved_columns']=[c['columns'] for c in children]
        return {'legal':True,'start':min(s['start'] for s in services),
            'end':max(s['end'] for s in services),'makespan':current.makespan,
            'delta_makespan':current.makespan-state.makespan,
            'duration':max(s['end'] for s in services)-min(s['start'] for s in services),
            'traffic':traffic,'cache_hit':False,'cache':current.cache,
            'resources':current.resources,'nets':current.nets,
            'details':details}
    cache = state.cache.copy()
    c = binding.get('read_cache')
    hit = False
    reused = 0
    duration = binding['ticks']
    reads = binding['external_read_words']
    scratch = dict(binding.get('scratch_by_site', {binding['site']: binding['scratch_words']}))
    details = {}
    if binding.get('resident_region'):
        spec=binding['resident_region']
        if (retention!='invalidate' or spec.get('kind')!='serial-native-resident-loop-v1' or c or
                set(spec.get('invalidate_read_cache',()))!=set(scratch)):
            return {'legal':False,'reason':'resident_cache_policy'}
        discarded=[]
        for site in sorted(scratch):
            old=cache.pop(site,None)
            if old:discarded.append({'site':site,'tag':old[0],'prefix':old[1],'words':old[2]})
        details={'cost_model':'serial-native-resident-loop-v1','retention':'invalidate',
            'discarded_read_cache':discarded,'external_read_words':reads,
            'external_write_words':binding['external_write_words'],'scratch_by_site':scratch}
        if binding.get('resident_overlap'):
            overlap=binding['resident_overlap']
            if (overlap.get('kind')!='commuting-native-actors-v1' or
                overlap.get('reservation')!='all-union-resources-through-final-ACK'):
                return {'legal':False,'reason':'resident_overlap_reservation'}
            details.update(cost_model='commuting-native-resident-loop-v1',overlap_proof=overlap['proof'],
                           reservation=overlap['reservation'])
    if binding.get('dot_tile'):
        spec=binding['dot_tile']
        if (retention!='invalidate' or spec.get('kind')!='prepared-s32-static-b-tile-v1' or
            spec.get('invalidate_read_cache')!=[binding['site']] or c):
            return {'legal':False,'reason':'tile_cache_policy'}
        discarded=[]
        for site in spec['invalidate_read_cache']:
            old=cache.pop(site,None)
            if old:
                discarded.append({'site':site,'tag':old[0],'prefix':old[1],'words':old[2]})
        details={'cost_model':'native-p-e-tile-stream-v1','retention':'invalidate',
                 'discarded_read_cache':discarded,'external_read_words':reads,
                 'external_write_words':binding['external_write_words'],'scratch_by_site':scratch}
    if c:
        old = cache.get(c['site'])
        matching = bool(old and old[0] == c['tag'])
        hit = bool(c['stripe'] and matching and old[1] >= c['stripe'])
        if c.get('cost_model') == 'dot-prefix-state-v2':
            if retention not in retention_actions(state, binding):
                return {'legal': False, 'reason': 'retention_policy'}
            reused = min(old[1], c['stripe']) if matching else 0
            saved = c['rows'] * c['components'][0] * reused
            reads -= saved
            duration -= saved * c['load_ticks']
            if retention == 'discard':
                cache.pop(c['site'], None)
            elif not c['stripe']:
                pass  # streaming only touches the scratch/zero slots
            else:
                retain = max(old[1], c['stripe']) if matching and retention == 'preserve' else c['stripe']
                cache[c['site']] = (c['tag'], retain, c['rows'] * c['components'][0] * retain)
            retained = cache.get(c['site'])
            retained_words = retained[2] if retained else 0
            scratch[c['site']] = max(scratch[c['site']], 9 + retained_words)
            details = {'cost_model': c['cost_model'], 'retention': retention,
                       'reused_prefix': reused, 'loaded_prefix': c['stripe'] - reused,
                       'retained_prefix': retained[1] if retained else 0,
                       'external_read_words': reads, 'external_write_words': binding['external_write_words'],
                       'scratch_by_site': scratch}
        else:
            if hit:
                duration = binding['warm_ticks']
                reads = binding['warm_read_words']
            if c['stripe']:
                cache[c['site']] = (c['tag'], c['stripe'], c['cache_words'])
            else:
                cache.pop(c['site'], None)
    for site, n in scratch.items():
        if n > hardware['sites'][site]['words']:
            return {'legal': False, 'reason': 'S_capacity'}
        if (not c or site != c['site']) and site in cache:
            if n > 8 or n + cache[site][2] + 1 > hardware['sites'][site]['words']:
                return {'legal': False, 'reason': 'S_overlap'}
    start = max([data_ready] + [state.resources[r][0] for r in binding['resources']])
    end = start + duration
    resources = state.resources.copy()
    for r in binding['resources']:
        resources[r] = tuple(sorted(resources[r][1:] + (end,)))
    makespan = max(state.makespan, end)
    if details:
        details.update(duration=duration, delta_makespan=makespan-state.makespan)
    return {'legal': True, 'start': start, 'end': end, 'makespan': makespan,
            'delta_makespan': makespan-state.makespan, 'duration': duration,
            'traffic': reads + binding['external_write_words'], 'cache_hit': hit,
            'cache': cache, 'resources': resources, 'nets': nets, 'details': details}
