"""Schedule unchanged finite-S event traces across independent actor streams.

Per-actor order remains fixed, including every S overwrite, M bank/context,
guard and ACK. Only different actors commute. Shared external addresses keep
all RAW/WAR/WAW obligations; copy descriptors exclude one another per declared
virtual channel. This is an explicit compiler model, not a full DMA timing proof.
"""
from dataclasses import dataclass,replace
import hashlib
import json

from resident_timing import audit,event_ticks


COPIES=frozenset(('LOAD','LOAD_ZERO','STORE','STORE_COMMIT'))
METADATA=frozenset(('REUSE','DISCARD'))


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def binding_channels(program,hardware,actor_map):
    """Resolve actual declared instance services, never infer them from names.

    Rebinding a frozen trace requires identical SRAM and descriptor timings.
    The channel index comes from the hardware input, not the template actor.
    """
    from memory import descriptor_ticks
    from resident_survey import build_actors
    if any(not hardware['tile_service_bindings'].get(role) for role in ('P','E')):
        raise ValueError('overlap binding lacks qualified instance services')
    build_actors({'hardware':hardware},program['service_timing'])
    actors=program['actors'];groups=hardware['tile_service_bindings'];result={};sites=set()
    if set(actor_map)!=set(actors):raise ValueError('overlap binding actor coverage differs')
    for name,a in actors.items():
        role={'M':'P','E':'E'}.get(a['kind']);group=actor_map[name]
        if role is None or group not in groups[role]:raise ValueError('overlap binding lacks qualified instance service')
        m=hardware['leaf_inventory'][group];s=hardware['sites'][m['site']]
        if m['site'] in sites:raise ValueError('overlap binding aliases a private actor store')
        sites.add(m['site'])
        if a['words']!=m['words'] or a['words']!=s['words'] or a['stride']!=(8 if a['kind']=='M' else 1):
            raise ValueError('overlap binding storage/operand contract differs')
        for direction,io,ticks in (('load','io_write_ticks','load_ticks'),('store','io_read_ticks','store_ticks')):
            if descriptor_ticks(hardware['virtual_memory'],1,direction,m[io])!=a[ticks]:
                raise ValueError('overlap binding descriptor service differs')
        result[name]=m['memory_group']%hardware['virtual_memory']['channels']
    return result


def build(graph,program,channel_by_actor):
    audit(program,program['service_timing'])
    actors=program['actors']
    if (set(channel_by_actor)!=set(actors) or any(type(v)!=int or v<0 for v in channel_by_actor.values()) or
        len({a.get('site',name) for name,a in actors.items()})!=len(actors)):
        raise ValueError('explicit independent actors and nonnegative memory channels required')
    if program.get('transports'):raise ValueError('candidate transports need a separate concurrent path contract')
    nodes=[];last_actor={};writers={};readers={};streams={name:[] for name in sorted(actors)}
    for i,event in enumerate(program['events']):
        op=event['op'];actor=event['actor'];deps=set()
        if actor in last_actor:deps.add(last_actor[actor])
        last_actor[actor]=i;streams[actor].append(i)
        if op not in COPIES|METADATA|{'M_TERM','M_FINAL','E'}:raise ValueError('unsupported concurrent resident event')
        address=None;write=False
        if op in COPIES or op=='REUSE' and event.get('where')=='external':
            address=event['external_address'];write=op in ('STORE','STORE_COMMIT')
            if type(address)!=int or address<0:raise ValueError('explicit external event address required')
            if address in writers:deps.add(writers[address])
            if write:
                deps.update(readers.get(address,()));writers[address]=i;readers[address]=set()
            else:readers.setdefault(address,set()).add(i)
        if op in COPIES:
            duration=actors[actor]['load_ticks' if op in ('LOAD','LOAD_ZERO') else 'store_ticks']
            channel=channel_by_actor[actor]
        else:duration=event_ticks(event,program['service_timing']);channel=None
        if type(duration)!=int or duration<0 or not duration and op not in METADATA:
            raise ValueError('positive native/copy service duration required')
        nodes.append({'event':i,'actor':actor,'duration':duration,'channel':channel,'deps':sorted(deps)})
    if sum(n['duration'] for n in nodes)!=program['total_ticks']:raise ValueError('trace changed serialized billing')
    return {'kind':'resident-actor-trace-dag-v1','graph_sha256':digest(graph),'program_sha256':digest(program),
        'channel_by_actor':dict(channel_by_actor),'streams':streams,'nodes':nodes,
        'serialized_ticks':program['total_ticks'],
        'scope':'fixed per-actor trace, external address hazards and serialized virtual descriptor channels; not full control/DMA/SystemC/physical timing'}


def first_gap(calendar,ready,duration):
    at=ready
    for start,end in calendar:
        if at+duration<=start:break
        if at<end:at=end
    return at


@dataclass(frozen=True)
class State:
    positions:tuple
    finishes:tuple
    calendars:tuple
    makespan:int=0
    history:int=-1
    active:tuple=()


def search(dag,*,width=8,policy='critical_path',backbone=None):
    """Each frontier adds one ready actor head and recomputes its real cost.

    Earliest free calendar gaps permit unrelated work before a previously
    reserved future descriptor. width=None enumerates the finite list-schedule
    action family; width=1 is the same-action greedy baseline, not FCFS alone.
    """
    if width is not None and (type(width)!=int or width<1):raise ValueError('positive overlap width required')
    if policy not in ('critical_path','makespan'):raise ValueError('unknown overlap rank policy')
    names=tuple(sorted(dag['streams']));streams=[dag['streams'][name] for name in names];nodes=dag['nodes'];count=len(nodes)
    channels=tuple(sorted(set(dag['channel_by_actor'].values())));channel_index={c:i for i,c in enumerate(channels)}
    if backbone is not None and backbone.get('dag_sha256')!=digest(dag):
        raise ValueError('overlap backbone belongs to another trace')
    if len(channels)==len(names):
        # With a private descriptor channel per actor, its stream edges already
        # serialize every exclusive resource. Earliest DAG times are feasible
        # and meet the critical-path lower bound; enumeration adds no choices.
        ends=[];rows=[]
        for n in nodes:
            start=max((ends[d] for d in n['deps']),default=0);end=start+n['duration'];ends.append(end)
            rows.append({'event':n['event'],'start':start,'end':end})
        return {'kind':'resident-actor-schedule-v1','dag_sha256':digest(dag),'makespan':max(ends,default=0),
            'decisions':rows,'width':width,'policy':policy,'expanded':count,'merged':0,'pruned':0,'bound_calls':1,
            'optimality':'critical-path bound attained for independent per-actor descriptor channels','scope':dag['scope']}
    initial=State(tuple(0 for _ in names),tuple(-1 for _ in nodes),tuple(() for _ in channels))
    # Integer predecessors avoid recursively comparing or deallocating deep
    # nested history tuples after a long native trace. History is not a key.
    trail=[]
    children=[[] for _ in nodes]
    for n in nodes:
        for dep in n['deps']:children[dep].append(n['event'])
    expanded=merged=pruned=bound_calls=0
    def lower(s):
        nonlocal bound_calls
        bound_calls+=1;ends=list(s.finishes)
        for n in nodes:
            i=n['event']
            if ends[i]>=0:continue
            ends[i]=max((ends[d] for d in n['deps']),default=0)+n['duration']
        return max(ends,default=0)
    def advance(s,ai):
        if s.positions[ai]>=len(streams[ai]):return None
        at=streams[ai][s.positions[ai]];n=nodes[at]
        if any(s.finishes[d]<0 for d in n['deps']):return None
        start=max((s.finishes[d] for d in n['deps']),default=0);cal=s.calendars
        if n['channel'] is not None:
            ci=channel_index[n['channel']];start=first_gap(cal[ci],start,n['duration'])
            rows=list(cal);rows[ci]=tuple(sorted((*rows[ci],(start,start+n['duration']))));cal=tuple(rows)
        ends=list(s.finishes);ends[at]=start+n['duration'];pos=list(s.positions);pos[ai]+=1
        active=[]
        for parent in s.active:
            for child in children[parent]:
                if ends[child]<0:active.append(parent);break
        if children[at]:active.append(at)
        active.sort()
        row={'event':at,'start':start,'end':ends[at]}
        trail.append((s.history,row))
        return replace(s,positions=tuple(pos),finishes=tuple(ends),calendars=cal,
                       makespan=max(s.makespan,ends[at]),history=len(trail)-1,active=tuple(active))
    def key(s):
        # Only completed values still read by an unfinished event affect the
        # future. Previous actor heads are among those DAG frontier values.
        # Maintain the live frontier incrementally. Besides avoiding a scan of
        # the complete trace for every state, this uses no nested generators
        # retaining whole states while inner iterators are closed early.
        relevant=tuple([(i,s.finishes[i]) for i in s.active])
        return s.positions,relevant,s.calendars
    def score(s):return (lower(s),s.makespan) if policy=='critical_path' else (s.makespan,lower(s))
    if backbone is not None:
        if backbone.get('dag_sha256')!=digest(dag):raise ValueError('overlap backbone belongs to another trace')
        order=[r['event'] for r in backbone['decisions']];seed=initial;prefix=[]
        for event in order:
            ai=next((i for i,row in enumerate(streams) if seed.positions[i]<len(row) and row[seed.positions[i]]==event),None)
            if ai is None:raise ValueError('overlap backbone is not an actor-head order')
            seed=advance(seed,ai)
            if seed is None:raise ValueError('overlap backbone violates a dependency')
            prefix.append(seed)
        if len(prefix)!=count:raise ValueError('overlap backbone does not finish the trace')
    else:prefix=[]
    states=[initial]
    for step in range(count):
        candidates=[]
        for s in states:
            for ai in range(len(names)):
                ns=advance(s,ai)
                if ns is not None:candidates.append(ns);expanded+=1
        if prefix:candidates.append(prefix[step])
        unique={}
        for s in candidates:
            k=key(s);old=unique.get(k)
            if old is None or s.makespan<old.makespan:unique[k]=s
        merged+=len(candidates)-len(unique);ordered=sorted(unique.values(),key=lambda s:(*score(s),s.positions,s.calendars))
        if width is not None:
            kept=ordered[:width]
            if prefix and not any(key(s)==key(prefix[step]) and s.makespan<=prefix[step].makespan for s in kept):
                kept=kept[:max(0,width-1)]+[prefix[step]]
            pruned+=max(0,len(ordered)-len(kept));states=kept
        else:states=ordered
        if not states:raise ValueError('overlap actor heads deadlocked')
    best=min(states,key=lambda s:s.makespan);rows=[];h=best.history
    while h>=0:previous,row=trail[h];rows.append(row);h=previous
    rows.reverse()
    return {'kind':'resident-actor-schedule-v1','dag_sha256':digest(dag),'makespan':best.makespan,
        'decisions':rows,'width':width,'policy':policy,'expanded':expanded,'merged':merged,'pruned':pruned,'bound_calls':bound_calls,
        'optimality':'finite actor-head earliest-gap list-schedule family only' if width is None else 'bounded search; no global optimality guarantee',
        'scope':dag['scope']}
