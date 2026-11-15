"""Exact constant-cost phases of the existing finite-S native tile recipe.

Each worker owns its M/S/LC/E throughout the enclosing compound. Only actual
one-word descriptors contend on channels, through their S-commit/STORE-ACK
boundary. Native P/feeder/E services already include their local adaptation.
No extra SRAM, DMA queue, bank/row state, latency calibration or energy model.
"""
from copy import deepcopy
from functools import lru_cache
import json
from types import SimpleNamespace

from memory import descriptor_ticks
from phase_program import aggregate,simulate


PROTOCOL={'kind':'native-tile-compound-fcfs-v1','reservation':'all-union-resources-through-final-ACK'}


def program(spec,qualification,memory,p_meta,e_meta=None):
    seq=lambda *nodes:{'sequence':list(nodes)}
    repeat=lambda n,body:{'repeat':n,'body':body}
    private=lambda ticks,kind:{'channel':-1,'ticks':ticks,'kind':kind}
    def transfer(meta,direction):
        return {'channel':meta['memory_group']%memory['channels'],
            'ticks':descriptor_ticks(memory,1,direction,meta['io_write_ticks' if direction=='load' else 'io_read_ticks']),
            'kind':'external-load-until-S-commit' if direction=='load' else 'external-store-until-ACK'}
    pl,ps=transfer(p_meta,'load'),transfer(p_meta,'store')
    rt,ct=spec['tile'];rows,columns,k=spec['rows'],spec['columns'],spec['K']
    parts=[repeat(16,pl)]
    def split(total,step):
        n,r=divmod(total,step)
        return [(s,c) for s,c in ((step,n),(r,int(bool(r)))) if c]
    for r,nr in split(rows,rt):
        p=qualification['P'][str(r)];feed=qualification['feeder'][str(r)]
        for n,nn in split(columns,ct):
            dot=repeat(k,seq(repeat(n,pl),*(seq(repeat(r,pl),
                private(feed['cold' if component==0 else 'reuse_b'],'tile-feeder'),
                private(p['scale'],'tile-scale'),private(p['execute'],'tile-execute')) for component in range(3))))
            if n==1:finish=repeat(r,seq(private(p['final_store'],'tile-final-store'),ps))
            else:
                if e_meta is None:raise ValueError('tile phase missing qualified E service')
                packed=r*((n+3)//4);p1=qualification['P']['1']
                finish=seq(repeat(packed,seq(private(p['final_store'],'tile-final-store'),ps)),
                    repeat(packed,seq(transfer(e_meta,'load'),private(qualification['e_shift_store'],'tile-E-service'),
                                      transfer(e_meta,'store'))),
                    repeat(r*n,seq(repeat(3,seq(pl,pl,
                        private(qualification['feeder']['1']['cold'],'tile-feeder'),
                        private(p1['scale'],'tile-scale'),private(p1['execute'],'tile-execute'))),
                        private(p1['final_store'],'tile-final-store'),ps)))
            parts.append(repeat(nr*nn,seq(dot,finish)))
    return seq(*parts)


def eligible(binding,hardware):
    if binding.get('phase_execution')!=PROTOCOL or 'tile_partition' not in binding:return False
    seen=set();shared=False;recipes=set();children=binding['parallel_shards']['children']
    for child in children:
        b=child['binding']
        if 'dot_tile' not in b or any(k in b for k in ('materialized_tile','read_cache','parallel_shards')):return False
        overlap=seen&set(b['resources'])
        if any(not r.startswith('virtual-memory.channel.') for r in overlap):return False
        if any(hardware['resources'][r]!=1 for r in b['resources']):return False
        shared|=bool(overlap);seen.update(b['resources']);s=b['dot_tile']
        recipes.add((s['rows'],s['K'],tuple(s['tile'])))
    m=hardware['virtual_memory']
    return shared and len(recipes)==1 and len(children)<=min(m[k] for k in ('credits','queue','slots'))


def timing_key(binding,hardware):
    q=hardware['tile_service_profiles'];s=binding['dot_tile']
    # IDs/addresses cannot affect this explicitly constant-cost phase model.
    spec={k:s[k] for k in ('rows','columns','K','tile')}
    def meta(group):
        m=hardware['leaf_inventory'][group]
        return {k:m[k] for k in ('memory_group','io_read_ticks','io_write_ticks')}
    p=meta(binding['macro_binding']['M'])
    e=meta(binding['macro_binding']['E']) if 'E' in binding['macro_binding'] else None
    return json.dumps([spec,q,hardware['virtual_memory'],p,e],sort_keys=True,separators=(',',':'))


@lru_cache(maxsize=8192)
def worker(key):
    body=program(*json.loads(key));ticks,counts=aggregate(body);return body,ticks,counts


@lru_cache(maxsize=8192)
def timed(keys,channels):
    result=simulate([worker(key)[0] for key in keys],channels)
    return {'makespan_ticks':result['makespan'],
        'worker_completion_ticks':[result['worker_completion'][i] for i in range(len(keys))],
        'phase_counts':result['phase_counts'],'arbitration':'FCFS-request-age-then-worker-ID',
        'reservation':'all-union-resources-through-final-ACK'}


def evaluate(state,binding,hardware,data_ready,policies,evaluate_leaf):
    if not eligible(binding,hardware):return {'legal':False,'reason':'tile_phase_contract'}
    children=binding['parallel_shards']['children']
    if not isinstance(policies,tuple) or len(policies)!=len(children):return {'legal':False,'reason':'retention_policy'}
    start=max([data_ready]+[state.resources[r][0] for r in binding['resources']]);cache=state.cache
    services=[];keys=[];traffic=0
    for i,(child,policy) in enumerate(zip(children,policies)):
        b=child['binding'];current=SimpleNamespace(resources=state.resources,cache=cache,nets=state.nets,makespan=state.makespan)
        ev=evaluate_leaf(current,b,hardware,start,retention=policy)
        if not ev['legal']:return ev
        key=timing_key(b,hardware);_,solo,counts=worker(key)
        if (solo!=ev['duration'] or counts['external-load-until-S-commit']!=b['external_read_words'] or
            counts['external-store-until-ACK']!=b['external_write_words']):raise ValueError('tile phase work/traffic changed')
        services.append({'id':binding['parallel_shards']['primitive']+'#columns-'+str(i),
            'binding':b['id'],'site':b['site'],'start':start,'end':ev['end'],'evaluation':dict(ev['details'])})
        cache=ev['cache'];traffic+=ev['traffic'];keys.append(key)
    result=deepcopy(timed(tuple(keys),hardware['virtual_memory']['channels']));peak=state.makespan
    for row,finish in zip(services,result['worker_completion_ticks']):
        wait=finish-(row['end']-row['start'])
        if wait<0:raise ValueError('tile phase arbitration removed work')
        row['end']=start+finish;row['evaluation'].update(channel_wait_ticks=wait,duration=finish,
            delta_makespan=max(peak,row['end'])-peak);peak=max(peak,row['end'])
    end=start+result['makespan_ticks'];resources=dict(state.resources)
    for r in binding['resources']:resources[r]=(end,)
    return {'legal':True,'start':start,'end':end,'duration':end-start,'makespan':max(state.makespan,end),
        'delta_makespan':max(state.makespan,end)-state.makespan,'resources':resources,'cache':cache,
        'nets':state.nets|frozenset(binding['nets']),'traffic':traffic,'cache_hit':False,
        'details':{'cost_model':'dot-phased-column-shards-v1','services':services,'phase_timing':result,
                   'delta_makespan':max(state.makespan,end)-state.makespan}}
