"""Independent timing reconstruction and proof projection for phase compounds.

Does not import the planner, its transition or its phase-program generator.
The small, independently tested FCFS event engine is shared as a simulation
primitive. All native phases are reconstructed here a second way. A verified
phase wait is projected into ordinary continuous private-resource service;
one extra proof-only child holds channels throughout the compound reservation.
Original arithmetic/traffic and native-cost verification remain separate.
"""
from collections import Counter,defaultdict
from copy import deepcopy

from memory import descriptor_ticks
from phase_program import simulate


def _program(leaf,row,hardware):
    c = leaf['read_cache'];e = row['evaluation']
    if c.get('cost_model') != 'dot-prefix-state-v2' or c['components'][1] != 1:
        raise ValueError('unsupported cooperative cache format')
    r,n,k,t = c['rows'],c['columns'],c['K'],c['stripe'];a = c['components'][0]
    hit = e['reused_prefix']
    if a not in (1,3) or not 0 <= hit <= t <= k or min(r,n,k) < 1:
        raise ValueError('invalid cooperative cache shape/state')
    group = leaf['macro_binding']['M'];meta = hardware['leaf_inventory'][group]
    mem = hardware['virtual_memory'];channel = meta['memory_group'] % mem['channels']
    lib = hardware['phase_native_templates'];p = lib['partial']['sequence'];f = lib['dot_final']
    if (len(p) != 4 or [p[0].get('native'),p[1].get('native'),p[3].get('native')] != ['M_SCALE','M_LOAD','M'] or
        [x.get('native') for x in p[2].get('sequence',[])] != ['M_LOAD','M_LOAD'] or
        f.get('native') != 'M_READ' or f.get('read_words') != 0 or f.get('write_words') != 1):
        raise ValueError('unrecognized cooperative native command grammar')
    sequence = lambda *nodes:{'sequence':list(nodes)}
    repeat = lambda count,node:{'repeat':count,'body':node}
    phase = lambda ch,ticks,kind:{'channel':ch,'ticks':ticks,'kind':kind}
    load = phase(channel,descriptor_ticks(mem,1,'load',meta['io_write_ticks']),'external-load-until-S-commit')
    store = phase(channel,descriptor_ticks(mem,1,'store',meta['io_read_ticks']),'external-store-until-ACK')
    read_s = phase(-1,meta['io_read_ticks'],'S-operand-read')
    def term(streamed):
        parts = []
        for component in range(a):
            parts.append(phase(-1,p[0]['ticks'],'M_SCALE'))
            if streamed:parts.append(load)
            parts.extend((read_s,phase(-1,p[1]['ticks'],'M_LOAD')))
            if component == 0:parts.append(load)
            parts.extend((read_s,phase(-1,p[2]['sequence'][0]['ticks'],'M_LOAD'),
                          read_s,phase(-1,p[2]['sequence'][1]['ticks'],'M_LOAD'),
                          phase(-1,p[3]['ticks'],'M')))
        return sequence(*parts)
    final = sequence(phase(-1,f['ticks'],'M_READ'),
                     phase(-1,meta['io_write_ticks'],'S-result-write'),store)
    return sequence(repeat(1+r*a*(t-hit),load),
                    repeat(r*n,sequence(repeat(t,term(False)),repeat(k-t,term(True)),final)))


def _measure(program):
    if 'sequence' in program:
        ticks = 0;counts = Counter()
        for node in program['sequence']:
            t,c = _measure(node);ticks += t;counts.update(c)
        return ticks,counts
    if 'repeat' in program:
        ticks,counts = _measure(program['body']);n = program['repeat']
        return ticks*n,Counter({k:v*n for k,v in counts.items()})
    return program['ticks'],Counter({program['kind']:int(program['ticks'] > 0)})


def project(tasks,hardware,plan):
    """Validate original reservation claims, then return a check-only view."""
    by_id = {t['id']:t for t in tasks}
    if len(by_id) != len(tasks):raise ValueError('duplicate phase source task')
    projected = {t['id']:{**t,'bindings':list(t['bindings'])} for t in tasks}
    rows = [];claims = defaultdict(list);checked = 0;peak = 0
    for row in plan['tasks']:
        if row['id'] not in by_id:raise ValueError('unknown phase source task')
        matches = [b for b in by_id[row['id']]['bindings'] if b['id'] == row['binding']]
        if len(matches) != 1:raise ValueError('unknown/ambiguous cooperative binding')
        binding = matches[0]
        if 'phase_execution' not in binding:
            if row.get('evaluation',{}).get('cost_model') == 'dot-phased-column-shards-v1':
                raise ValueError('phase evaluation without declared binding protocol')
            if 'parallel_shards' in binding:
                services = row['evaluation']['services']
                for child,s in zip(binding['parallel_shards']['children'],services):
                    for resource in child['binding']['resources']:claims[resource].append((s['start'],s['end']))
            else:
                for resource in binding['resources']:
                    offsets=binding.get('materialized_tile',{}).get('resource_offsets',{})
                    a,b=offsets.get(resource,(0,row['end']-row['start']))
                    claims[resource].append((row['start']+a,row['start']+b))
            rows.append(row);peak = max(peak,row['end']);continue
        if (binding['phase_execution'] != {'kind':'isolated-compound-fcfs-v1',
                 'reservation':'all-union-resources-through-final-ACK'} or 'frontier_partition' in binding):
            raise ValueError('unknown cooperative reservation protocol')
        for resource in binding['resources']:
            if hardware['resources'][resource] != 1:raise ValueError('cooperative reservation needs exclusive resources')
            claims[resource].append((row['start'],row['end']))
        e = row['evaluation'];children = binding['parallel_shards']['children'];services = e.get('services',[])
        if (set(e) != {'cost_model','services','phase_timing','delta_makespan'} or
            e['cost_model'] != 'dot-phased-column-shards-v1' or len(children) != len(services)):
            raise ValueError('cooperative service coverage/evaluation differs')
        if len(children) > min(hardware['virtual_memory'][k] for k in ('queue','slots','credits')):
            raise ValueError('cooperative requests exceed declared finite storage/credits')
        seen = set();seen_sites = set();programs = [];recipes=set()
        for child,s in zip(children,services):
            leaf = child['binding'];resources = set(leaf['resources'])
            if leaf['site'] in seen_sites or set(leaf['macro_binding']) != {'M'}:
                raise ValueError('cooperative children share private storage or non-M operation')
            if any(not r.startswith('virtual-memory.channel.') for r in seen & resources):
                raise ValueError('cooperative children share a private context/port/controller')
            seen |= resources;seen_sites.add(leaf['site'])
            program = _program(leaf,s,hardware);ticks,counts = _measure(program)
            c = leaf['read_cache'];h = s['evaluation']['reused_prefix']
            recipes.add((c['rows'],c['K'],tuple(c['components']),c['stripe']))
            solo = leaf['ticks']-h*c['rows']*c['components'][0]*c['load_ticks']
            if (ticks != solo or counts['external-load-until-S-commit'] != s['evaluation']['external_read_words'] or
                counts['external-store-until-ACK'] != leaf['external_write_words']):
                raise ValueError('independent cooperative native work/traffic differs')
            programs.append(program)
        if len(recipes)!=1:raise ValueError('cooperative children use different K-prefix recipes')
        timed = simulate(programs,hardware['virtual_memory']['channels'])
        expected = {'makespan_ticks':timed['makespan'],
            'worker_completion_ticks':[timed['worker_completion'][i] for i in range(len(children))],
            'phase_counts':timed['phase_counts'],'arbitration':'FCFS-request-age-then-worker-ID',
            'reservation':'all-union-resources-through-final-ACK'}
        if e['phase_timing'] != expected or row['end']-row['start'] != timed['makespan']:
            raise ValueError('independent cooperative event timing differs')
        clone = deepcopy(binding);clone.pop('phase_execution')
        converted = deepcopy(row);converted['evaluation'].pop('phase_timing')
        converted['evaluation']['cost_model'] = 'dot-column-shards-v1'
        prefix = peak
        for i,(child,s) in enumerate(zip(clone['parallel_shards']['children'],converted['evaluation']['services'])):
            leaf = child['binding'];c = leaf['read_cache'];ev = s['evaluation']
            solo = leaf['ticks']-ev['reused_prefix']*c['rows']*c['components'][0]*c['load_ticks']
            wait = expected['worker_completion_ticks'][i]-solo
            if (s['start'] != row['start'] or s['end'] != row['start']+expected['worker_completion_ticks'][i] or
                ev.get('channel_wait_ticks') != wait or wait < 0 or ev['duration'] != s['end']-s['start'] or
                ev['delta_makespan'] != max(prefix,s['end'])-prefix):
                raise ValueError('cooperative child wait/time/causality differs')
            prefix = max(prefix,s['end'])
            ev.pop('channel_wait_ticks')
            leaf['ticks'] += wait;leaf['warm_ticks'] += wait
            leaf['resources'] = [r for r in leaf['resources'] if not r.startswith('virtual-memory.channel.')]
        # This synthetic child exists only in this checker projection, never
        # in executable arithmetic or in the original candidate/action pool.
        channels = [r for r in binding['resources'] if r.startswith('virtual-memory.channel.')]
        ident = binding['parallel_shards']['primitive']+'#columns-'+str(len(children))
        hold = {'id':ident,'site':binding['site'],'macro_binding':{},'resources':channels,
                'nets':[],'ticks':row['end']-row['start'],'scratch_words':0,'scratch_by_site':{},
                'external_read_words':0,'external_write_words':0}
        clone['parallel_shards']['children'].append({'columns':[0,0],'binding':hold,'proof_only':'channel reservation'})
        converted['evaluation']['services'].append({'id':ident,'binding':ident,'site':binding['site'],
            'start':row['start'],'end':row['end']})
        projected[row['id']]['bindings'] = [clone if b['id'] == clone['id'] else b for b in projected[row['id']]['bindings']]
        rows.append(converted);peak = max(peak,row['end']);checked += 1
    for resource,intervals in claims.items():
        live = 0
        events = [(start,1) for start,end in intervals]+[(end,-1) for start,end in intervals]
        for _,delta in sorted(events):
            live += delta
            if not 0 <= live <= hardware['resources'][resource]:
                raise ValueError('cooperative/global reservation contention '+resource)
        if live:raise ValueError('cooperative reservation not released')
    return list(projected.values()),{**plan,'tasks':rows},{'cooperative_compounds':checked,
        'scope':'independent phase reconstruction plus conservative full-union reservation proof; not RTL arbitration'}
