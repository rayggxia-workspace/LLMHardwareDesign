"""Independent actual-time audit for fixed-offset resource insertion calendars."""
from collections import defaultdict


def audit(tasks,hardware,plan):
    spec=hardware['window_calendar']
    if spec.get('kind')!='fixed-offset-calendar-v1' or set(spec)!={'kind','resources'}:
        raise ValueError('unknown independent window contract')
    names=spec['resources'];calendar=set(names)
    if len(names)!=len(calendar) or any(hardware['resources'].get(r)!=1 for r in names):
        raise ValueError('invalid exclusive window capacity')
    for meta in hardware.get('leaf_inventory',{}).values():
        if 'M' in meta['macros'] and meta['io_resource'] in calendar:
            raise ValueError('window calendar breaks persistent M-cache order')
    by_id={t['id']:t for t in tasks};claims=defaultdict(list);count=0
    for row in plan['tasks']:
        if row['id'] not in by_id:raise ValueError('unknown window task')
        matches=[b for b in by_id[row['id']]['bindings'] if b['id']==row['binding']]
        if len(matches)!=1:raise ValueError('unknown/ambiguous window binding')
        binding=matches[0];duration=row['end']-row['start'];offsets={}
        if 'materialized_tile' in binding:
            from verify_materialized_tile import check_windows
            _,offsets,_,_=check_windows(binding,hardware);count+=1
            if not set(offsets)<=calendar:raise ValueError('missing auxiliary window resources')
        expected={}
        for resource in set(binding['resources'])&calendar:
            lo,hi=offsets.get(resource,(0,duration))
            if not 0<=lo<hi<=duration:raise ValueError('window exceeds service lifetime')
            expected[resource]=[row['start']+lo,row['start']+hi]
            claims[resource].append(tuple(expected[resource]))
        if ('resource_windows' in row or plan.get('calendar_kind')=='fixed-offset-calendar-v1') and row.get('resource_windows')!=expected:
            raise ValueError('emitted resource windows differ from independent contract')
    for resource,intervals in claims.items():
        last=0
        for a,b in sorted(intervals):
            if type(a)!=int or type(b)!=int or not last<=a<b:
                raise ValueError('actual window contention '+resource)
            last=b
    return {'passed':True,'materialized_tasks':count,'resources':len(claims),
        'scope':'independent actual-time interval claims; native work, S and dependencies audited separately'}
