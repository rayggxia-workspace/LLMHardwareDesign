"""Serial resident-program attribution, separate from chip utilization."""
from collections import Counter

from resident_timing import audit,event_ticks
from verify_cover_frontier import verify


def report(ir,plan):
    check=verify(ir['tasks'],ir['hardware'],ir['resident_actions'],plan)
    actions={a['id']:a for a in ir['resident_actions']};rows=[]
    for row in plan['tasks']:
        if row['id'] not in actions:continue
        b=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding'])
        recipe=ir['resident_recipes'][b['resident_region']['recipe']];p=recipe['plan'];audit(p,ir['resident_timing'])
        services=Counter();copies=Counter();footprint={n:set() for n in p['actors']};zeros=Counter();traffic=Counter()
        count=recipe['loop']['elements'];programs=[p];weights=[count]
        if recipe.get('continuation_loop'):
            from resident_continuation import visits
            from verify_resident_continuation import verify as verify_sequence
            sequence=recipe['continuation_loop'];programs=sequence['programs'];weights=visits(sequence)
            verify_sequence(recipe['graph'],recipe['loop'],sequence,p['actors'],p['zero_address'],ir['resident_timing'])
        for body,n in zip(programs,weights):
            audit(body,ir['resident_timing'])
            for e in body['events']:
                actor=e['actor'];kind=e['op']
                if kind in ('LOAD','LOAD_ZERO','STORE'):
                    copies[actor]+=n*p['actors'][actor]['store_ticks' if kind=='STORE' else 'load_ticks']
                    footprint[actor].add(e['address'])
                    if kind=='LOAD_ZERO':zeros[actor]+=n;category='guard_zero_reads'
                    elif kind=='STORE':category='live_out_stores' if e['record'] in recipe['graph']['live_out'].values() else 'intermediate_spills'
                    else:
                        obj=recipe['graph']['objects'][e['record']]
                        category=('constant_reads' if obj['kind']=='constant' or 'literal' in obj else
                                  'intermediate_reloads' if obj['kind']=='produced' else 'input_reads')
                    traffic[category]+=n
                else:
                    services[actor]+=n*event_ticks(e,ir['resident_timing'])
                    if kind in ('M_FINAL','E'):footprint[actor].add(e['address'])
        total=sum(services.values())+sum(copies.values())
        if total!=row['end']-row['start']:raise ValueError('resident utilization duration differs')
        actors={}
        for actor,a in p['actors'].items():
            used=len(footprint[actor]);mapped=b['resident_region']['actor_map'][actor]
            actors[mapped]={'capacity_words':a['words'],'distinct_accessed_words_per_element':used,
                'accessed_capacity_fraction':used/a['words'],'native_service_ticks_per_element':services[actor]/count,
                'copy_ticks_per_element':copies[actor]/count,
                'native_service_fraction_of_reservation':services[actor]/total,
                'repeated_zero_load_words':zeros[actor]}
        rows.append({'id':row['id'],'binding':row['binding'],'elements':recipe['loop']['elements'],
            'duration_ticks':row['end']-row['start'],'actors':actors,
            'copy_fraction_of_serial_cost':sum(copies.values())/total,
            'program_bodies':len(programs),'continued':bool(recipe.get('continuation_loop')),
            'logical_external_word_categories':dict(traffic)})
    return {'passed':True,'schedule_audit':check,'resident_services':rows,
        'scope':'serial generated event/copy model and whole-service reservations, not measured DRAM bytes, pure-core/chip utilization, SystemC, energy or token/s',
        'next_question':'inspect input versus constant/guard/intermediate traffic, active footprint versus whole-S reservation, and actual legal multi-element/data-path reuse; no free packing or transport'}
