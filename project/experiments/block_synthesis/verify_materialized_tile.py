"""Independent three-phase tile arithmetic/work/window contract reconstruction.

No candidate-builder or search imports. The original streaming alternative must
remain in the common pool and independently pass its original native audit.
"""
from copy import deepcopy

from memory import descriptor_ticks


KIND='packed-external-three-phase-v1'


def contract(binding,h):
    s=binding['dot_tile'];q=h['tile_service_profiles'];pgroup=binding['macro_binding']['M']
    egroup=binding['macro_binding']['E'];p=h['leaf_inventory'][pgroup];e=h['leaf_inventory'][egroup]
    if 'M' in e['macros']:raise ValueError('auxiliary tile group cannot own a cached M')
    pl=descriptor_ticks(h['virtual_memory'],1,'load',p['io_write_ticks'])
    ps=descriptor_ticks(h['virtual_memory'],1,'store',p['io_read_ticks'])
    el=descriptor_ticks(h['virtual_memory'],1,'load',e['io_write_ticks'])
    es=descriptor_ticks(h['virtual_memory'],1,'store',e['io_read_ticks'])
    rows,cols,k=s['rows'],s['columns'],s['K'];rt,ct=s['tile']
    if ct<=1:raise ValueError('materialized tile needs an E conversion')
    def sizes(total,step):
        full,tail=divmod(total,step)
        return {v:c for v,c in ((step,full),(tail,int(bool(tail)))) if c}
    dot=16*pl;convert=0;scatter=16*pl;packed=0
    for r,nr in sizes(rows,rt).items():
        for n,nn in sizes(cols,ct).items():
            count=nr*nn;pr=q['P'][str(r)];fr=q['feeder'][str(r)]
            dot+=count*k*((3*r+n)*pl+3*(pr['scale']+pr['execute'])+fr['cold']+2*fr['reuse_b'])
            if n==1:dot+=count*r*(pr['final_store']+ps);continue
            saves=count*r*((n+3)//4);packed+=saves
            dot+=saves*(pr['final_store']+ps)
            convert+=saves*(el+q['e_shift_store']+es)
            scatter+=count*r*n*(6*pl+3*(q['feeder']['1']['cold']+q['P']['1']['scale']+
                q['P']['1']['execute'])+q['P']['1']['final_store']+ps)
    primary={pgroup+'.M',pgroup+'.M.context',pgroup+'.LC.service',p['io_resource'],
        'virtual-memory.channel.'+str(p['memory_group']%h['virtual_memory']['channels'])}
    auxiliary=set(binding['resources'])-primary
    if not auxiliary or any(h['resources'].get(r)!=1 for r in auxiliary):
        raise ValueError('invalid auxiliary tile resources')
    phases=[{'name':name,'offset':off,'ticks':ticks} for name,off,ticks in
        (('dot-packed',0,dot),('E-flags',dot,convert),('scatter',dot+convert,scatter))]
    return phases,{r:[dot,dot+convert] for r in sorted(auxiliary)},pl,packed


def check_windows(binding,h):
    s=binding['materialized_tile'];phases,offsets,pl,packed=contract(binding,h)
    if (s.get('kind')!=KIND or s.get('phases')!=phases or s.get('resource_offsets')!=offsets or
        s.get('extra_P_zero_loads')!=16 or binding['ticks']!=sum(p['ticks'] for p in phases)):
        raise ValueError('materialized tile phase/resource timing differs')
    region=s.get('external_region',{})
    if (set(region)!={'address_words','words','record_bytes'} or region.get('record_bytes')!=16 or
        type(region.get('address_words'))!=int or region['address_words']<0 or
        type(region.get('words'))!=int or region['words']<2*packed):
        raise ValueError('materialized packed/flag region too small/invalid')
    return phases,offsets,pl,packed


def verify(ir,task,binding):
    from verify_tile_binding import verify as verify_stream
    h=ir['hardware'];spec=binding['materialized_tile']
    matches=[b for b in task['bindings'] if b['id']==spec.get('stream_binding') and 'materialized_tile' not in b]
    if len(matches)!=1:raise ValueError('original streaming tile absent/ambiguous')
    old=matches[0];verify_stream(ir,task,old)
    phases,offsets,pl,packed=check_windows(binding,h)
    expected=deepcopy(old);expected['id']+=';materialized-E-window'
    region=ir.get('materialized_external_regions',{}).get(task['id'])
    expected['materialized_tile']={'kind':KIND,'stream_binding':old['id'],'external_region':region,
        'phases':phases,'resource_offsets':offsets,'extra_P_zero_loads':16}
    work=expected['tile_work'];work['ticks']+=16*pl;work['external_read_words']+=16
    work['external_words']+=16;work['initial_zero_loads']+=16
    work['temporary_external_words']=2*packed
    work.update(context='full K per grid; packed STORE ACKs before E; P reinitialized before scatter',
        reservation='primary whole; auxiliary only E segment through flag STORE ACK',cost_model=KIND)
    expected['ticks']=work['ticks'];expected['external_read_words']=work['external_read_words']
    if binding!=expected:raise ValueError('materialized native work/traffic/source contract differs')
    calendar=h.get('window_calendar',{})
    if calendar.get('kind')!='fixed-offset-calendar-v1' or not set(offsets)<=set(calendar.get('resources',[])):
        raise ValueError('materialized tile missing auxiliary window calendar')
    return 1
