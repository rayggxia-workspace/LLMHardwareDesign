"""Expose an actual E window by materializing packed values in external RAM.

Same qualified M/E/S commands; two extra groups of eight zero LOADs before
scatter. The primary P stays leased throughout. No new accumulator, local
copy, packing engine or speculative S hit is supplied by this transformation.
"""
from copy import deepcopy

from memory import descriptor_ticks


KIND='packed-external-three-phase-v1'


def phases(binding,hardware):
    s=binding['dot_tile'];w=binding['tile_work'];q=hardware['tile_service_profiles']
    p=hardware['leaf_inventory'][binding['macro_binding']['M']]
    e=hardware['leaf_inventory'][binding['macro_binding']['E']]
    m=hardware['virtual_memory']
    pl=descriptor_ticks(m,1,'load',p['io_write_ticks']);ps=descriptor_ticks(m,1,'store',p['io_read_ticks'])
    el=descriptor_ticks(m,1,'load',e['io_write_ticks']);es=descriptor_ticks(m,1,'store',e['io_read_ticks'])
    rt,ct=s['tile'];k=s['K'];a=16*pl;c=16*pl
    def split(total,step):
        n,r=divmod(total,step)
        return [(v,count) for v,count in ((step,n),(r,int(bool(r)))) if count]
    for r,nr in split(s['rows'],rt):
        ptime=q['P'][str(r)];feed=q['feeder'][str(r)]
        for n,nn in split(s['columns'],ct):
            count=nr*nn
            a+=count*(k*(3*r+n)*pl+k*(3*(ptime['scale']+ptime['execute'])+feed['cold']+2*feed['reuse_b']))
            if n==1:a+=count*r*(ptime['final_store']+ps)
            else:
                a+=count*r*((n+3)//4)*(ptime['final_store']+ps)
                p1=q['P']['1']
                c+=count*r*n*(3*(2*pl+q['feeder']['1']['cold']+p1['scale']+p1['execute'])+p1['final_store']+ps)
    b=w['packed_outputs']*(el+q['e_shift_store']+es)
    if a+b+c!=binding['ticks']+16*pl:raise ValueError('materialized tile phase time not conserved')
    return a,b,c,pl


def variants_for(ir):
    if 'materialized_tile_scope' in ir:raise ValueError('materialized tiles already registered')
    h=ir['hardware'];limit=(1<<h['virtual_memory']['address_bits'])//16
    if h.get('external_capacity_words') is not None:limit=min(limit,h['external_capacity_words'])
    cursor=ir['required_external_bytes']//16;regions={};added=0;interval=set()
    for task in ir['tasks']:
        originals=[b for b in task['bindings'] if b.get('dot_tile') and b['dot_tile']['tile'][1]>1]
        originals=[b for b in originals if 'M' not in h['leaf_inventory'][b['macro_binding']['E']]['macros']]
        if not originals:continue
        size=max(2*b['tile_work']['packed_outputs'] for b in originals)
        if cursor+size>limit:continue
        region={'address_words':cursor,'words':size,'record_bytes':16}
        regions[task['id']]=region;cursor+=size
        for old in originals:
            a,b,c,pl=phases(old,h);new=deepcopy(old);new['id']+=';materialized-E-window'
            primary_group=old['macro_binding']['M'];p=h['leaf_inventory'][primary_group]
            egroup=old['macro_binding']['E'];e=h['leaf_inventory'][egroup]
            primary={primary_group+'.M',primary_group+'.M.context',primary_group+'.LC.service',p['io_resource'],
                'virtual-memory.channel.'+str(p['memory_group']%h['virtual_memory']['channels'])}
            auxiliary=set(old['resources'])-primary
            if not auxiliary or any(h['resources'][r]!=1 for r in auxiliary):continue
            interval.update(auxiliary)
            new['materialized_tile']={'kind':KIND,'stream_binding':old['id'],'external_region':deepcopy(region),
                'phases':[{'name':name,'offset':offset,'ticks':ticks} for name,offset,ticks in
                    (('dot-packed',0,a),('E-flags',a,b),('scatter',a+b,c))],
                'resource_offsets':{r:[a,a+b] for r in sorted(auxiliary)},'extra_P_zero_loads':16}
            work=new['tile_work'];work['ticks']+=16*pl;work['external_read_words']+=16
            work['external_words']+=16;work['initial_zero_loads']+=16
            work['temporary_external_words']=2*work['packed_outputs']
            work['context']='full K per grid; packed STORE ACKs before E; P reinitialized before scatter'
            work['reservation']='primary whole; auxiliary only E segment through flag STORE ACK'
            work['cost_model']=KIND
            new['ticks']=work['ticks'];new['external_read_words']=work['external_read_words']
            task['bindings'].append(new);added+=1
    # Calendar metadata changes the planner, never a physical capacity.
    if added:
        interval.update(r for r in h['resources'] if r.startswith('virtual-memory.channel.'))
        h['window_calendar']={'kind':'fixed-offset-calendar-v1','resources':sorted(interval)}
    ir['materialized_external_regions']=regions;ir['required_external_bytes']=cursor*16
    ir['materialized_tile_scope']={'added_bindings':added,'extra_external_bytes':sum(x['words'] for x in regions.values())*16,
        'scope':'full external packed/flag arrays, actual zero refill, primary lease and delayed E window',
        'excluded':'new hardware, general dirty S, moving live M accumulators, DMA bank/row overlap, MC/LC binary or system qualification'}
    return ir
