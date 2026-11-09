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
        services=Counter();copies=Counter();footprint={n:set() for n in p['actors']};zeros=Counter()
        for e in p['events']:
            actor=e['actor'];kind=e['op']
            if kind in ('LOAD','LOAD_ZERO','STORE'):
                copies[actor]+=p['actors'][actor]['store_ticks' if kind=='STORE' else 'load_ticks']
                footprint[actor].add(e['address'])
                if kind=='LOAD_ZERO':zeros[actor]+=1
            else:
                services[actor]+=event_ticks(e,ir['resident_timing'])
                if kind in ('M_FINAL','E'):footprint[actor].add(e['address'])
        actors={}
        for actor,a in p['actors'].items():
            used=len(footprint[actor]);mapped=b['resident_region']['actor_map'][actor]
            actors[mapped]={'capacity_words':a['words'],'distinct_accessed_words_per_element':used,
                'accessed_capacity_fraction':used/a['words'],'native_service_ticks_per_element':services[actor],
                'copy_ticks_per_element':copies[actor],
                'native_service_fraction_of_reservation':services[actor]/p['total_ticks'],
                'repeated_zero_load_words':zeros[actor]*recipe['loop']['elements']}
        rows.append({'id':row['id'],'binding':row['binding'],'elements':recipe['loop']['elements'],
            'duration_ticks':row['end']-row['start'],'actors':actors,
            'copy_fraction_of_serial_cost':p['copy_ticks']/p['total_ticks']})
    return {'passed':True,'schedule_audit':check,'resident_services':rows,
        'scope':'serial generated event/copy model and whole-service reservations, not measured DRAM bytes, pure-core/chip utilization, SystemC, energy or token/s',
        'next_question':'cold per-element loops reinitialize guard words and discard reusable constants; carrying proven finite-S/padding/B-bank state across iterations is a candidate requiring generated-program and full-loop proof'}
