"""Opt-in cooperative Dot compounds with state-dependent descriptor phases.

This is a common backend/action pool, not an algorithm gain. The entire union
of the compound's resources is reserved until its final ACK. Descriptor phases
may interleave ONLY among its independently owned children. Other tasks cannot
enter this reservation. This conservative first integration does not pretend
to provide a general cross-task event frontier or real bank/row arbitration.
"""
from copy import deepcopy
from functools import lru_cache
import json
from types import SimpleNamespace

from phase_program import cached_dot_program, aggregate, simulate, PhaseEventLimit


PROTOCOL = {'kind':'isolated-compound-fcfs-v1',
            'reservation':'all-union-resources-through-final-ACK'}


def eligible(binding, hardware):
    if 'frontier_partition' in binding or 'parallel_shards' not in binding:return False
    children = binding['parallel_shards']['children']
    shared = set();seen = set();sites = set();recipes = set()
    for child in children:
        b = child['binding'];c = b.get('read_cache',{})
        if (c.get('cost_model') != 'dot-prefix-state-v2' or c.get('components',[0,0])[1] != 1 or
            set(b.get('macro_binding',{})) != {'M'} or b['site'] in sites):return False
        sites.add(b['site'])
        recipes.add((c['rows'],c['K'],tuple(c['components']),c['stripe']))
        resources = set(b['resources']);overlap = resources & seen
        if any(not r.startswith('virtual-memory.channel.') for r in overlap):return False
        shared |= overlap;seen |= resources
        if any(hardware['resources'][r] != 1 for r in resources):return False
    memory = hardware['virtual_memory']
    if len(children) > min(memory['queue'],memory['credits'],memory['slots']):return False
    # Common-recipe gang scheduling is the declared first action family.
    # Different K-prefix loop bodies need a broader exact timing strategy;
    # their original serial compounds remain in the shared candidate pool.
    return bool(shared) and len(recipes)==1


def variants_for(ir):
    if 'phased_compound_scope' in ir:raise ValueError('phased compounds already added')
    if 'column_shard_scope' not in ir:raise ValueError('registered column candidates required')
    hardware = ir['hardware'];added = 0
    hardware['phase_native_templates'] = deepcopy(ir['native_templates'])
    for task in ir['tasks']:
        generated = []
        for binding in task['bindings']:
            if eligible(binding,hardware):
                b = deepcopy(binding);b['id'] += ';phases=fcfs'
                b['phase_execution'] = dict(PROTOCOL);generated.append(b)
        task['bindings'].extend(generated);added += len(generated)
    ir['phased_compound_scope'] = {'added_bindings':added,'protocol':dict(PROTOCOL),
        'scope':'constant native/descriptor phase costs; finite S and original scalar arithmetic unchanged',
        'excluded':'heterogeneous K-prefix recipes (old serial choices retained), other-task overlap within a compound reservation, real banks/rows/queues, tile packing, RTL qualification'}
    return ir


@lru_cache(maxsize=8192)
def _worker_program(serialized):
    """Memoize symbolic programs by every actual timing/shape input.

    Names/addresses do not affect the explicitly constant-cost model. Use a
    canonical private-site name, while the real transition separately checks
    each physical site's capacity, source identity, live prefix and ACKs.
    """
    c,hit,meta,memory,library=json.loads(serialized)
    row={'evaluation':{'reused_prefix':hit,'scratch_by_site':{'S':0}}}
    program=cached_dot_program({'read_cache':c},row,library,meta,memory)
    ticks,counts=aggregate(program)
    return program,ticks,counts


@lru_cache(maxsize=8192)
def _timed(worker_keys, channels):
    result = simulate([_worker_program(key)[0] for key in worker_keys],channels)
    return {'makespan_ticks':result['makespan'],
            'worker_completion_ticks':list(result['worker_completion'][i] for i in range(len(result['worker_completion']))),
            'phase_counts':result['phase_counts'], 'arbitration':'FCFS-request-age-then-worker-ID',
            'reservation':'all-union-resources-through-final-ACK'}


def evaluate(state, binding, hardware, data_ready, policies, evaluate_leaf):
    if binding.get('phase_execution') != PROTOCOL or not eligible(binding,hardware):
        return {'legal':False,'reason':'phase_contract'}
    children = binding['parallel_shards']['children']
    if not isinstance(policies,tuple) or len(policies) != len(children):
        return {'legal':False,'reason':'retention_policy'}
    start = max([data_ready]+[state.resources[r][0] for r in binding['resources']])
    cache = state.cache;services = [];worker_keys = [];traffic = 0
    for i,(child,policy) in enumerate(zip(children,policies)):
        b = child['binding']
        current = SimpleNamespace(resources=state.resources,cache=cache,nets=state.nets,makespan=state.makespan)
        ev = evaluate_leaf(current,b,hardware,start,retention=policy)
        if not ev['legal']:return ev
        c = b['read_cache'];group = b['macro_binding']['M']
        meta = {**hardware['leaf_inventory'][group], 'words':hardware['sites'][c['site']]['words']}
        row = {'id':binding['parallel_shards']['primitive']+'#columns-'+str(i),
               'binding':b['id'],'site':b['site'],'start':start,'end':ev['end'],
               'cache_hit':ev['cache_hit'],'evaluation':dict(ev['details'])}
        if ev['details']['scratch_by_site'][c['site']]>meta['words']:
            raise ValueError('phase worker exceeds actual finite private S')
        canonical={k:c[k] for k in ('cost_model','rows','columns','K','components','stripe')}
        canonical['site']='S'
        timing_meta={k:meta[k] for k in ('words','memory_group','io_read_ticks','io_write_ticks')}
        library={k:hardware['phase_native_templates'][k] for k in ('partial','dot_final')}
        key=json.dumps([canonical,ev['details']['reused_prefix'],timing_meta,
                        hardware['virtual_memory'],library],sort_keys=True,separators=(',',':'))
        _,ticks,counts = _worker_program(key)
        if (ticks != ev['duration'] or counts['external-load-until-S-commit'] != ev['details']['external_read_words'] or
            counts['external-store-until-ACK'] != b['external_write_words']):
            raise ValueError('cooperative phase program changes native work/traffic')
        cache = ev['cache'];services.append(row);worker_keys.append(key);traffic += ev['traffic']
    # Timing keys contain only immutable constant-cost programs. Source names
    # and addresses cannot affect this declared conservative model; the actual
    # reused-prefix and shape are already represented in these programs.
    try:timed = deepcopy(_timed(tuple(worker_keys),hardware['virtual_memory']['channels']))
    except PhaseEventLimit as error:
        error.diagnostic.update(binding=binding['id'],programs=[_worker_program(key)[0] for key in worker_keys])
        raise
    peak = state.makespan
    for row,finish in zip(services,timed['worker_completion_ticks']):
        active = row['end']-row['start'];wait = finish-active
        if wait < 0:raise ValueError('phase arbitration removed private work')
        row['end'] = start+finish
        row['evaluation'].update(channel_wait_ticks=wait,duration=finish,
            delta_makespan=max(peak,row['end'])-peak)
        peak = max(peak,row['end'])
    end = start+timed['makespan_ticks'];resources = state.resources.copy()
    for r in binding['resources']:resources[r] = (end,)
    makespan = max(state.makespan,end)
    return {'legal':True,'start':start,'end':end,'makespan':makespan,
            'delta_makespan':makespan-state.makespan,'duration':end-start,
            'traffic':traffic,'cache_hit':False,'cache':cache,'resources':resources,
            'nets':state.nets|frozenset(binding['nets']),
            'details':{'cost_model':'dot-phased-column-shards-v1','services':services,
                       'phase_timing':timed,'delta_makespan':makespan-state.makespan}}
