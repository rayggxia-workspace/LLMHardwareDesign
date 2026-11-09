"""Independent order/hazard/resource certificate for commuting trace events.

Does not rebuild the planner DAG or call its scheduling/calendar code. A valid
original finite-S program and this certificate imply the same word operations;
the base program's actual-value/RTL evidence is still separately required.
"""
import hashlib
import json
from functools import lru_cache

from resident_timing import audit,event_ticks


def verify(graph,program,dag,schedule,channel_by_actor):
    def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (dag.get('graph_sha256')!=digest(graph) or dag.get('program_sha256')!=digest(program) or
        schedule.get('dag_sha256')!=digest(dag) or schedule.get('kind')!='resident-actor-schedule-v1' or
        dag['channel_by_actor']!=channel_by_actor):
        raise ValueError('overlap source/dag/schedule binding differs')
    audit(program,program['service_timing']);events=program['events'];rows=schedule['decisions']
    if (len(rows)!=len(events) or any(type(r['event'])!=int for r in rows) or
        sorted(r['event'] for r in rows)!=list(range(len(events)))):raise ValueError('overlap event coverage differs')
    by_event={r['event']:r for r in rows};actors=program['actors'];last={};accesses={};channels={};busy={n:0 for n in actors}
    nodes=dag['nodes']
    if len(nodes)!=len(events):raise ValueError('overlap DAG event coverage differs')
    expected_streams={actor:[i for i,e in enumerate(events) if e['actor']==actor] for actor in actors}
    if dag['streams']!=expected_streams:raise ValueError('overlap DAG actor stream coverage differs')
    @lru_cache(maxsize=None)
    def precedes(before,after):
        pending=list(nodes[after]['deps']);seen=set()
        while pending:
            i=pending.pop()
            if i==before:return True
            if i<before or i in seen:continue
            seen.add(i);pending.extend(nodes[i]['deps'])
        return False
    if (set(channel_by_actor)!=set(actors) or any(type(c)!=int or c<0 for c in channel_by_actor.values()) or
        len({a.get('site',name) for name,a in actors.items()})!=len(actors) or program.get('transports')):
        raise ValueError('overlap channel/actor/path contract differs')
    for i,e in enumerate(events):
        r=by_event[i];actor=e['actor'];op=e['op']
        if op not in ('LOAD','LOAD_ZERO','STORE','STORE_COMMIT','REUSE','DISCARD','M_TERM','M_FINAL','E'):
            raise ValueError('unsupported overlapping event')
        if type(r['start'])!=int or type(r['end'])!=int or r['start']<0:raise ValueError('invalid overlap time')
        copy=op in ('LOAD','LOAD_ZERO','STORE','STORE_COMMIT')
        if copy:duration=actors[actor]['load_ticks' if op in ('LOAD','LOAD_ZERO') else 'store_ticks']
        else:duration=event_ticks(e,program['service_timing'])
        if duration<0 or duration==0 and op not in ('REUSE','DISCARD'):raise ValueError('invalid overlap duration')
        if r['end']!=r['start']+duration:raise ValueError('overlap event service changed')
        node=nodes[i]
        if (node['event']!=i or node['actor']!=actor or node['duration']!=duration or
            node['channel']!=(channel_by_actor[actor] if copy else None) or
            any(type(d)!=int or not 0<=d<i for d in node['deps'])):
            raise ValueError('overlap DAG service/dependency differs')
        if actor in last and last[actor] not in node['deps']:raise ValueError('overlap DAG private actor order missing')
        if actor in last and by_event[last[actor]]['end']>r['start']:raise ValueError('overlap changed a private actor order')
        last[actor]=i;busy[actor]+=duration
        if copy:channels.setdefault(dag['channel_by_actor'][actor],[]).append((r['start'],r['end'],i))
        if copy or op=='REUSE' and e.get('where')=='external':
            accesses.setdefault(e['external_address'],[]).append((i,op in ('STORE','STORE_COMMIT')))
    conflicts=0
    for rows in accesses.values():
        # All pair conflicts, rather than relying on the planner's last-writer
        # or reader-set reconstruction, also catch WAR and WAW scratch aliases.
        for i,write in rows:
            if not write:continue
            for j,_ in rows:
                if i==j:continue
                before,after=sorted((i,j))
                if by_event[before]['end']>by_event[after]['start']:raise ValueError('overlap external RAW/WAR/WAW hazard')
                if not precedes(before,after):raise ValueError('overlap DAG external hazard dependency missing')
                conflicts+=1
    for rows in channels.values():
        rows.sort()
        if any(a[1]>b[0] for a,b in zip(rows,rows[1:])):raise ValueError('overlap virtual descriptor channel conflict')
    end=max((r['end'] for r in by_event.values()),default=0)
    if end!=schedule['makespan'] or end>program['total_ticks']:raise ValueError('overlap makespan differs or exceeds serialized trace')
    return {'passed':True,'events':len(events),'makespan':end,'serialized_ticks':program['total_ticks'],
        'actor_busy_ticks':busy,'actor_utilization':{n:t/end if end else 0 for n,t in busy.items()},
        'external_conflict_checks':conflicts,'external_words':program['external_words'],
        'scope':'per-actor finite-S/guard/bank/ACK order preserved and all shared external hazards/channel exclusions checked; base numeric and full DMA/control/physical qualification remain separate'}
