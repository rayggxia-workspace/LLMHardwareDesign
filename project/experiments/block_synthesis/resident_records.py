"""Bounded DP over whole-record residency for a native SSA region.

Copy cost, plus optional measured services, is optimized here. Compute order remains the supplied native
order, each M operation owns its entire accumulator, and all actions serialize.
This is not registered in the full-model scheduler or qualified as RTL yet.
"""
from dataclasses import dataclass,replace


@dataclass(frozen=True)
class History:
    previous:object
    events:tuple


@dataclass(frozen=True)
class State:
    slots:tuple
    backed:frozenset
    padding:tuple
    banks:tuple
    cost:int=0
    loads:int=0
    stores:int=0
    history:object=None
    service_ticks:int=0


def plan(graph,actors,zero_address,*,width=8,spill_all=False,rank_policy='copy_cost',service_timing=None):
    """Choose placement/replacement from each current state, never fixed ticks.

    Actors explicitly supply kind, finite words, LOAD/STORE copy ticks and
    stride. M needs an eight-record guarded cell for actual wide B reads;
    E uses one whole word. No cross-S path is assumed: dirty remote data is
    first STORE-ACKed, then LOAD-ACKed. All initial records must have addresses.
    width=None is exhaustive for finite small cases; bounded runs are heuristic.
    """
    if width is not None and (type(width)!=int or width<1):raise ValueError('positive residency width required')
    if rank_policy not in ('copy_cost','future_copies'):raise ValueError('unknown resident rank policy')
    from resident_timing import event_ticks,validate
    if service_timing is not None:validate(service_timing)
    if type(zero_address)!=int or zero_address<0:raise ValueError('explicit external zero record required')
    if not actors:raise ValueError('native actors required')
    names=tuple(sorted(actors));meta=[actors[x] for x in names]
    if len({a.get('site',name) for name,a in zip(names,meta)})!=len(names):
        raise ValueError('shared-S actors require a common physical allocator')
    for a in meta:
        if (a.get('kind') not in ('M','E') or type(a.get('words'))!=int or a['words']<1 or
            a.get('stride')!=(8 if a['kind']=='M' else 1) or
            any(type(a.get(k))!=int or a[k]<1 for k in ('load_ticks','store_ticks'))):
            raise ValueError('finite actor/copy contract required')
    obj=graph['objects'];ops=graph['operations'];live_out=set(graph['live_out'].values())
    from resident_bounds import FutureCopies
    bound=FutureCopies(graph,actors) if rank_policy=='future_copies' else None
    bound_position=(0,None)
    def score(s):return s.cost+(bound.bound(s,*bound_position) if bound else 0)
    if any(type(v.get('external_address'))!=int or v['external_address']<0 for v in obj.values()):
        raise ValueError('all SSA records need reserved external addresses')
    last={}
    for i,n in enumerate(ops):
        for x in n['inputs']:last[x]=i
    produced={n['output'] for n in ops}
    if len(produced)!=len(ops):raise ValueError('native SSA output identity repeated')
    def event(s,*events,cost=0,loads=0,stores=0):
        service=sum(event_ticks(e,service_timing) for e in events)
        return replace(s,cost=s.cost+cost+service,service_ticks=s.service_ticks+service,
                       loads=s.loads+loads,stores=s.stores+stores,
                       history=History(s.history,events))
    def slot(s,actor,at,value):
        rows=list(s.slots);row=list(rows[actor]);row[at]=value;rows[actor]=tuple(row)
        return replace(s,slots=tuple(rows))
    def locate(s,actor,value):
        try:return s.slots[actor].index(value)
        except ValueError:return None
    def store(s,actor,at):
        value=s.slots[actor][at]
        if value is None:raise ValueError('STORE from empty resident cell')
        if value not in produced or value in s.backed:return s
        e={'op':'STORE','actor':names[actor],'address':at*meta[actor]['stride'],
           'record':value,'external_address':obj[value]['external_address'],'wait_ack':True}
        return event(replace(s,backed=s.backed|{value}),e,cost=meta[actor]['store_ticks'],stores=1)
    def evict(s,actor,at,needed):
        value=s.slots[actor][at]
        if value is not None and value in needed:s=store(s,actor,at)
        return slot(s,actor,at,None)
    def allocations(s,actor,protected,needed):
        free=[i for i,x in enumerate(s.slots[actor]) if x is None]
        # Empty cells within the same padding class are symmetric. Keep both
        # classes for M: choosing a new cell versus an initialized victim can
        # have a different future cost. Occupied records are never conflated.
        empty=[]
        for initialized in (True,False):
            choices=[i for i in free if (i in s.padding[actor])==initialized]
            if choices:empty.append(choices[0])
        if meta[actor]['kind']=='E' and free:empty=[free[0]]
        if free and (meta[actor]['kind']=='E' or any(i in s.padding[actor] for i in free)):
            # In this uniform-cell copy model an initialized empty cell
            # dominates deleting another resident word. Address-dependent
            # route/bank costs would require a different contract and proof.
            yield s,empty[0];return
        candidates=empty+[i for i,x in enumerate(s.slots[actor]) if x is not None and i not in protected]
        for at in candidates:yield evict(s,actor,at,needed),at
    def pad(s,actor,at):
        if meta[actor]['kind']!='M' or at in s.padding[actor]:return s
        pads=list(s.padding);pads[actor]=pads[actor]|{at};s=replace(s,padding=tuple(pads))
        events=tuple({'op':'LOAD_ZERO','actor':names[actor],'address':at*8+i,
                      'external_address':zero_address,'wait_ack':True} for i in range(1,8))
        return event(s,*events,cost=7*meta[actor]['load_ticks'],loads=7)
    def ensure(s,actor,value,protected,needed):
        at=locate(s,actor,value)
        if at is not None:
            yield pad(s,actor,at),at;return
        if value in produced and value not in s.backed:
            owner=next(((ai,locate(s,ai,value)) for ai in range(len(names)) if locate(s,ai,value) is not None),None)
            if owner is None:raise ValueError('lost dirty SSA record '+value)
            s=store(s,*owner)
        for ns,at in allocations(s,actor,protected,needed):
            ns=slot(ns,actor,at,value);ns=pad(ns,actor,at)
            e={'op':'LOAD','actor':names[actor],'address':at*meta[actor]['stride'],
               'record':value,'external_address':obj[value]['external_address'],'wait_ack':True}
            yield event(ns,e,cost=meta[actor]['load_ticks'],loads=1),at
    def trim(states):
        unique={}
        for s in states:
            key=(s.slots,s.backed,s.padding,s.banks)
            old=unique.get(key)
            if old is None or (s.cost,s.loads+s.stores)<(old.cost,old.loads+old.stores):unique[key]=s
        result=sorted(unique.values(),key=lambda s:(score(s),s.cost,s.loads+s.stores,s.stores,repr(s.slots),repr(s.banks)))
        return result if width is None else result[:width]
    initial=State(tuple((None,)*(a['words']//a['stride']) for a in meta),frozenset(),
                  tuple(frozenset() for _ in names),tuple(None for _ in names))
    states=[initial];expanded=0
    for index,n in enumerate(ops):
        future={x for x,i in last.items() if i>index}|live_out
        all_states=[]
        for actor,a in enumerate(meta):
            if a['kind']!=n['kind']:continue
            bound_position=(index,None)
            active=[(s,()) for s in states]
            if n['kind']=='M':
                for ti,t in enumerate(n['terms']):
                    more=[];remaining={x for term in n['terms'][ti:] for x in (term['a'],term['b'])}|future
                    for s,_ in active:
                        for sa,aa in ensure(s,actor,t['a'],set(),remaining):
                            reuse=sa.banks[actor]==t['b']
                            bs=[(sa,None)] if reuse else ensure(sa,actor,t['b'],{aa},remaining)
                            for sb,bb in bs:
                                banks=list(sb.banks);banks[actor]=t['b'];sb=replace(sb,banks=tuple(banks))
                                e={'op':'M_TERM','actor':names[actor],'native':n['id'],'a':aa*8,
                                   'b':None if reuse else bb*8,'a_record':t['a'],'b_record':t['b'],
                                   'reuse_b':reuse,'clear':ti==0,'k':n['k'],
                                   'coefficient':t['coefficient'],'scale_shift':t['scale_shift']}
                                more.append(event(sb,e));expanded+=1
                    bound_position=(index,ti+1)
                    active=[(s,()) for s in trim(more)]
            else:
                for value in n['inputs']:
                    more=[]
                    for s,addresses in active:
                        protected={at for at in addresses}
                        for ns,at in ensure(s,actor,value,protected,future|set(n['inputs'])):
                            more.append((ns,addresses+(at,)));expanded+=1
                    # Address tuples are semantically relevant until the E
                    # command reads every source; do not merge them away.
                    active=sorted(more,key=lambda x:(score(x[0]),x[0].cost,x[0].loads+x[0].stores,repr(x[0].slots)))
                    if width is not None:active=active[:width]
            for s,addresses in active:
                for ns,dst in allocations(s,actor,set(),future):
                    ns=slot(ns,actor,dst,n['output'])
                    if n['kind']=='M':
                        e={'op':'M_FINAL','actor':names[actor],'native':n['id'],'record':n['output'],
                           'address':dst*8,'width':n['width'],'shift':n['shift'],'wait_s_ack':True}
                    else:
                        e={'op':'E','actor':names[actor],'native':n['id'],'record':n['output'],
                           'inputs':[x*a['stride'] for x in addresses],'input_records':n['inputs'],
                           'address':dst*a['stride'],'opcode':n['opcode'],'shift':n['shift'],'wait_s_ack':True}
                    ns=event(ns,e)
                    if spill_all:
                        ns=store(ns,actor,dst)
                        ns=replace(ns,slots=tuple((None,)*len(row) for row in ns.slots),
                                   backed=ns.backed&future,banks=tuple(None for _ in names))
                    else:
                        ns=replace(ns,slots=tuple(tuple(x if x in future else None for x in row) for row in ns.slots),
                                   backed=ns.backed&future,
                                   banks=tuple(x if x in future else None for x in ns.banks))
                    all_states.append(ns)
        bound_position=(index+1,None);states=trim(all_states)
        if not states:return {'status':'no_plan','at_native':n['id'],'expanded':expanded}
    final=[]
    for s in states:
        for value in sorted(live_out):
            if value in s.backed:continue
            owner=next(((ai,locate(s,ai,value)) for ai in range(len(names)) if locate(s,ai,value) is not None),None)
            if owner is None:raise ValueError('lost live output')
            s=store(s,*owner)
        final.append(s)
    best=min(final,key=lambda s:(s.cost,s.loads+s.stores,s.stores));events=[];h=best.history
    while h is not None:events.append(h.events);h=h.previous
    result=[e for chunk in reversed(events) for e in chunk]
    return {'status':'planned','copy_ticks':best.cost-best.service_ticks,
            'native_service_ticks':best.service_ticks,'total_ticks':best.cost,'service_timing':service_timing,
            'external_load_words':best.loads,
            'external_store_words':best.stores,'external_words':best.loads+best.stores,
            'events':result,'actors':actors,'zero_address':zero_address,'expanded':expanded,'width':width,
            'spill_all':spill_all,'rank_policy':rank_policy,'bound_calls':bound.calls if bound else 0,
            'scope':'serial native region with optional measured P/E/feeder slots and explicit copy model; not full scheduler, MC/LC/DMA/system or energy qualification'}
