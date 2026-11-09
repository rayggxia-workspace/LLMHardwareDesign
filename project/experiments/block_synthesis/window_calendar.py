"""Pure fixed-offset insertion calendars for explicitly qualified service windows.

Whole-service resource claims remain the default. M-private IO stays append-only
so the read-cache decision order remains its physical order. A future auxiliary
booking must not hide the idle prefix before that booking from another task.
"""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

from transition import evaluate_transition


def resources(hardware):
    spec=hardware.get('window_calendar')
    if spec is None:return frozenset()
    if spec.get('kind')!='fixed-offset-calendar-v1' or set(spec)!={'kind','resources'}:
        raise ValueError('unknown window calendar contract')
    names=spec['resources']
    if len(names)!=len(set(names)) or any(hardware['resources'].get(r)!=1 for r in names):
        raise ValueError('window calendars require declared exclusive resources')
    for meta in hardware.get('leaf_inventory',{}).values():
        if 'M' in meta['macros'] and meta['io_resource'] in names:
            raise ValueError('M-private IO must preserve cache decision order')
    return frozenset(names)


def earliest(bookings,claims,ready):
    """Earliest integer translation of rigid half-open intervals; no time scan."""
    at=ready
    while True:
        moved=at
        for resource,(lo,hi) in claims.items():
            for a,b in bookings.get(resource,()):
                if at+lo<b and a<at+hi:
                    moved=max(moved,b-lo)
        if moved==at:return at
        at=moved


def insert(bookings,claims,start):
    result=dict(bookings)
    for resource,(lo,hi) in claims.items():
        intervals=sorted((*bookings.get(resource,()),(start+lo,start+hi)))
        merged=[]
        for a,b in intervals:
            if merged and a<merged[-1][1]:raise ValueError('window insertion overlap')
            if merged and a==merged[-1][1]:merged[-1]=(merged[-1][0],b)
            else:merged.append((a,b))
        result[resource]=tuple(merged)
    return result


def _shift_details(details,shift,prefix):
    result=deepcopy(details)
    for child in result.get('services',[]):
        child['start']+=shift;child['end']+=shift
        if 'evaluation' in child:
            child['evaluation']=_shift_details(child['evaluation'],shift,prefix)
            child['evaluation']['delta_makespan']=max(prefix,child['end'])-prefix
        prefix=max(prefix,child['end'])
    return result


def evaluate(state,binding,hardware,data_ready,**kwargs):
    calendar=resources(hardware)
    if not calendar:return evaluate_transition(state,binding,hardware,data_ready,**kwargs)
    proxy=SimpleNamespace(resources={r:((0,) if r in calendar else slots)
                                     for r,slots in state.resources.items()},
        cache=state.cache,nets=state.nets,makespan=state.makespan)
    ev=evaluate_transition(proxy,binding,hardware,data_ready,**kwargs)
    if not ev['legal']:return ev
    offsets=binding.get('materialized_tile',{}).get('resource_offsets',{})
    if set(offsets)-calendar or set(offsets)-set(binding['resources']):
        raise ValueError('service offset outside calendar/resources')
    claims={r:tuple(offsets.get(r,(0,ev['duration']))) for r in binding['resources'] if r in calendar}
    if any(len(pair)!=2 or any(type(v)!=int for v in pair) or not 0<=pair[0]<pair[1]<=ev['duration']
           for pair in claims.values()):raise ValueError('invalid service resource window')
    start=earliest(state.windows,claims,ev['start']);shift=start-ev['start']
    end=ev['end']+shift;new_resources={}
    for r,slots in ev['resources'].items():
        if r in calendar:new_resources[r]=(0,);continue
        # Shift the slots assigned by this transition, never an unrelated slot.
        retained=Counter(slots)&Counter(state.resources[r])
        assigned=Counter(slots)-retained
        new_resources[r]=tuple(sorted(list(retained.elements())+
            [at+shift for at in assigned.elements()]))
    details=_shift_details(ev['details'],shift,state.makespan)
    makespan=max(state.makespan,end)
    if details:details['delta_makespan']=makespan-state.makespan
    return {**ev,'start':start,'end':end,'makespan':makespan,
        'delta_makespan':makespan-state.makespan,'details':details,'resources':new_resources,
        'windows':insert(state.windows,claims,start),
        'resource_windows':{r:[start+a,start+b] for r,(a,b) in sorted(claims.items())}}
