"""Pure state-dependent evaluation shared by greedy and bounded frontier DP.

No input state or binding is mutated. Existing serial command/LOAD/STORE
semantics are retained; no transfer/computation overlap is assumed.
"""


def retention_actions(state, binding):
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
                        fixed=frozenset(), conflicts=(), wire_budget=None):
    nets = state.nets | frozenset(binding['nets'])
    if any(pair <= nets | fixed for pair in conflicts):
        return {'legal': False, 'reason': 'static_conflict'}
    wire_cost = sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    if wire_budget is not None and wire_cost > wire_budget:
        return {'legal': False, 'reason': 'wire_budget'}
    cache = state.cache.copy()
    c = binding.get('read_cache')
    hit = False
    reused = 0
    duration = binding['ticks']
    reads = binding['external_read_words']
    scratch = dict(binding.get('scratch_by_site', {binding['site']: binding['scratch_words']}))
    details = {}
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
