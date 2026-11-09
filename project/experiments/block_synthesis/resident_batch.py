"""State-dependent finite-S row grouping, layout and replacement search.

An M cell is eight real 128-bit words. It may hold a contiguous row vector,
or one scalar with seven explicit guard words. Moving between those layouts
is paid through acknowledged external backing; there is no invented gather.
"""
from dataclasses import dataclass,replace

from resident_batch_graph import digest,units,verify


ZERO='@written-zero'


@dataclass(frozen=True)
class State:
    cells:tuple
    backed:frozenset=frozenset()
    banks:tuple=()
    cost:int=0
    copies:int=0
    loads:int=0
    stores:int=0
    history:int=-1
    completed:frozenset=frozenset()


def validate_timing(rows,scalar):
    from resident_timing import validate
    validate(scalar)
    if (rows.get('kind')!='native-resident-row-services-v1' or
        len(rows.get('proof',{}).get('logs_sha256',[]))!=3 or
        len(rows['proof'].get('cases_per_initialization',[]))!=3 or
        any(n<1 for n in rows['proof']['cases_per_initialization']) or
        set(rows.get('profile',{}))!={'P','feeder'} or not rows.get('rtl_sha256')):
        raise ValueError('qualified multi-row service timing required')
    if any(scalar['rtl_sha256'].get(k)!=v for k,v in rows['rtl_sha256'].items()):
        raise ValueError('scalar and row service RTL differ')
    for boundary in rows['profile'].values():
        for table in boundary.values():
            if not table or any(type(v)!=int or v<1 for v in table.values()):raise ValueError('positive row service slots required')


def event_ticks(event,row_timing,scalar_timing):
    p=row_timing['profile'];op=event['op']
    try:
        if op=='ROW_M_TERM':
            r=str(event['rows'])
            return p['P'][r]['0']+p['P'][r][str(event['k'])]+p['feeder'][r][str(int(event['reuse_b']))]
        if op=='ROW_M_FINAL':return p['P'][str(event['rows'])][str(64+(1 if event['width']==16 else 2)*64+event['shift'])]
        if op=='E':
            from resident_timing import event_ticks as scalar_ticks
            return scalar_ticks(event,scalar_timing)
        if op in ('LOAD','LOAD_ZERO','STORE','STORE_COMMIT'):return 0
        raise ValueError('unknown row allocator event')
    except KeyError as exc:raise ValueError('unmeasured row service shape or format') from exc


def plan(tile,actors,zero_address,row_timing,scalar_timing,*,width=8,allow_batch=True,rank_policy='future_copies',
         schedule='fixed',grouping_policy='windows',operand_contract=None):
    verify(tile);validate_timing(row_timing,scalar_timing)
    from resident_operand_contract import validate as validate_operands
    masked=validate_operands(operand_contract,row_timing)
    if width is not None and (type(width)!=int or width<1):raise ValueError('positive batch frontier width required')
    if rank_policy not in ('copy_cost','future_copies','future_layout'):raise ValueError('unknown batch frontier ranking')
    if schedule not in ('fixed','ready'):raise ValueError('unknown native scheduling family')
    if grouping_policy not in ('windows','all'):raise ValueError('unknown ready grouping policy')
    if type(zero_address)!=int or not 0<=zero_address<tile['scratch_start']:raise ValueError('explicit external zero address required')
    names=tuple(sorted(actors));meta=[actors[n] for n in names]
    if (not names or {a['kind'] for a in meta}!={'M','E'} or
        len({a['site'] for a in meta})!=len(meta)):raise ValueError('independent declared M/E stores required')
    for a in meta:
        stride=8 if a['kind']=='M' else 1
        if (type(a['words'])!=int or a['words']<stride or a['words']%stride or a['stride']!=stride or
            any(type(a[t])!=int or a[t]<1 for t in ('load_ticks','store_ticks'))):raise ValueError('finite batch actor/copy contract required')
    graph=tile['graph'];objects=graph['objects'];groups=units(tile);nodes={n['id']:n for n in graph['operations']}
    from resident_ready import ReadyGraph
    ready_graph=ReadyGraph(tile,max(int(r) for r in row_timing['profile']['P']))
    remaining_service={}
    if schedule=='ready':
        for name,n in ready_graph.nodes.items():
            if n['kind']=='E':remaining_service[name]=event_ticks({'op':'E','opcode':n['opcode'],
                'shift':n['shift'],'inputs':n['inputs']},row_timing,scalar_timing)
            else:
                choices=[]
                for r in range(1,(ready_graph.max_rows if allow_batch else 1)+1):
                    try:
                        term=min(event_ticks({'op':'ROW_M_TERM','rows':r,'k':n['k'],'reuse_b':b},row_timing,scalar_timing) for b in (False,True))
                        final=event_ticks({'op':'ROW_M_FINAL','rows':r,'width':n['width'],'shift':n['shift']},row_timing,scalar_timing)
                        choices.append(len(n['terms'])*term//r+final)
                    except ValueError as exc:
                        if str(exc)!='unmeasured row service shape or format':raise
                if not choices:raise ValueError('native operation has no measured row service')
                remaining_service[name]=min(choices)
    produced={n['output'] for n in graph['operations']};live={c['record'] for c in graph['external_commits']}
    last={};writer={}
    for i,u in enumerate(groups):
        for member in u['members']:
            n=nodes[member];writer[n['output']]=i
            for value in n['inputs']:last[value]=i
    first_needs=[{} for _ in range(len(groups)+1)]
    for i in range(len(groups)-1,-1,-1):
        needs=dict(first_needs[i+1])
        offsets={}
        unit=groups[i];members=[nodes[m] for m in unit['members']]
        for member in reversed(unit['members']):
            n=nodes[member]
            for value in n['inputs']:offsets.setdefault(value,{0})
        if allow_batch and unit['batchable'] and len(members)>1:
            for rr,n in enumerate(members):
                for term in n['terms']:offsets[term['a']].add(rr)
        for member in reversed(unit['members']):
            n=nodes[member]
            for value in n['inputs']:needs[value]=(n['kind'],frozenset(offsets[value]))
        first_needs[i]=needs
    trail=[];expanded=merged=pruned=0;position=0
    def emit(s,events,*,copy=0,loads=0,stores=0):
        service=sum(event_ticks(e,row_timing,scalar_timing) for e in events)
        trail.append((s.history,tuple(events)))
        return replace(s,cost=s.cost+copy+service,copies=s.copies+copy,
                       loads=s.loads+loads,stores=s.stores+stores,history=len(trail)-1)
    def cell(s,ai,at,values):
        rows=list(s.cells);row=list(rows[ai]);row[at]=tuple(values);rows[ai]=tuple(row)
        return replace(s,cells=tuple(rows))
    def locations(s,value):
        return [(ai,at,j) for ai,row in enumerate(s.cells) for at,entry in enumerate(row)
                for j,x in enumerate(entry) if x==value]
    def store(s,ai,at,j,*,target=None,commit_for=None):
        value=s.cells[ai][at][j]
        if value in (None,ZERO):raise ValueError('batch STORE has no live record')
        canonical=objects[value]['external_address'];target=canonical if target is None else target
        if target==canonical and (value not in produced or value in s.backed):return s
        e={'op':'STORE' if commit_for is None else 'STORE_COMMIT','actor':names[ai],
           'address':at*meta[ai]['stride']+j,'record':value,'external_address':target,'wait_ack':True}
        if commit_for is not None:e['commit_for']=commit_for
        s=emit(s,[e],copy=meta[ai]['store_ticks'],stores=1)
        return replace(s,backed=s.backed|{value}) if target==canonical else s
    def evict(s,ai,at,needed,overwrite=None):
        count=len(s.cells[ai][at]) if overwrite is None else overwrite
        for value in dict.fromkeys(s.cells[ai][at][:count]):
            if value in (None,ZERO) or value not in needed or value not in produced or value in s.backed:continue
            owners=locations(s,value)
            if not any(a!=ai or c!=at or j>=count for a,c,j in owners):
                j=s.cells[ai][at].index(value);s=store(s,ai,at,j)
        return cell(s,ai,at,[x if j>=count or x==ZERO else None for j,x in enumerate(s.cells[ai][at])])
    def allocations(s,ai,protected,needed,overwrite=None):
        # Empty cells are symmetric only within the same written-zero class.
        free={};occupied=[]
        for at,entry in enumerate(s.cells[ai]):
            if at in protected:continue
            if overwrite is not None:
                if all(x in (None,ZERO) for x in entry[:overwrite]):free.setdefault(entry[overwrite:],at)
                else:occupied.append(at)
            elif all(x in (None,ZERO) for x in entry):free.setdefault(tuple(x==ZERO for x in entry),at)
            else:occupied.append(at)
        fullzero=(True,)*meta[ai]['stride']
        choices=[free[fullzero]] if overwrite is None and fullzero in free else [*free.values(),*occupied]
        for at in choices:yield evict(s,ai,at,needed,overwrite),at
    def ensure(s,ai,records,protected,needed):
        stride=meta[ai]['stride']
        if not records or len(records)>stride or any(x not in objects for x in records):raise ValueError('invalid batch operand layout')
        pattern=tuple(records)+(ZERO,)*(stride-len(records))
        active_prefix=masked and meta[ai]['kind']=='M'
        for at,entry in enumerate(s.cells[ai]):
            if active_prefix and entry[:len(records)]==tuple(records):yield s,at;return
            if entry==pattern:yield s,at;return
            if not active_prefix and entry[:len(records)]==tuple(records) and all(x in (None,ZERO) for x in entry[len(records):]):
                events=[{'op':'LOAD_ZERO','actor':names[ai],'address':at*stride+j,
                         'external_address':zero_address,'wait_ack':True} for j in range(len(records),stride) if entry[j]!=ZERO]
                ns=emit(s,events,copy=len(events)*meta[ai]['load_ticks'],loads=len(events)) if events else s
                yield cell(ns,ai,at,pattern),at;return
        for value in dict.fromkeys(records):
            if value in produced and value not in s.backed:
                owners=locations(s,value)
                if not owners:raise ValueError('batch lost a dirty native value')
                s=store(s,*owners[0])
        overwrite=len(records) if active_prefix else None
        for ns,at in allocations(s,ai,protected,needed,overwrite):
            events=[];entry=ns.cells[ai][at]
            for j,value in enumerate(tuple(records) if active_prefix else pattern):
                if value==ZERO:
                    if entry[j]==ZERO:continue
                    e={'op':'LOAD_ZERO','actor':names[ai],'address':at*stride+j,'external_address':zero_address,'wait_ack':True}
                else:e={'op':'LOAD','actor':names[ai],'address':at*stride+j,'record':value,
                        'external_address':objects[value]['external_address'],'wait_ack':True}
                events.append(e)
            ns=emit(ns,events,copy=len(events)*meta[ai]['load_ticks'],loads=len(events))
            yield cell(ns,ai,at,tuple(records)+entry[len(records):] if active_prefix else pattern),at
    def bound(s):
        if rank_policy=='copy_cost':return 0
        # At most one first future consumption per record is charged. Layout
        # changes and storage conflicts are relaxed, so this is optimistic.
        if schedule=='ready':
            requests={}
            for name,n in ready_graph.nodes.items():
                if name in s.completed:continue
                for value in n['inputs']:
                    if value not in ready_graph.writers or ready_graph.writers[value] in s.completed:
                        requests.setdefault(value,set()).add(n['kind'])
            # Unknown future order relaxes the consumer kind and row offset.
            first={v:(kinds,frozenset(range(8))) for v,kinds in requests.items()}
        else:first={value:request for value,request in first_needs[position].items() if value not in writer or writer[value]<position}
        owners_by_value={}
        for ai,row in enumerate(s.cells):
            for entry in row:
                for offset,value in enumerate(entry):
                    if value not in (None,ZERO):owners_by_value.setdefault(value,set()).add((ai,offset))
        # A relaxed per-node share of measured services prevents a frontier
        # from favoring histories merely because they postpone expensive
        # arithmetic. Sharing and B reuse are assumed optimistically here;
        # actual transitions still pay every native command and final ACK.
        cost=sum(v for name,v in remaining_service.items() if name not in s.completed) if schedule=='ready' else 0
        for value,(kind,offsets) in first.items():
            ais=[i for i,a in enumerate(meta) if a['kind'] in kind] if schedule=='ready' else [i for i,a in enumerate(meta) if a['kind']==kind]
            owners=owners_by_value.get(value,set())
            local=any(ai in ais and (rank_policy!='future_layout' or kind=='E' or offset in offsets) for ai,offset in owners)
            if local or any(meta[i]['kind']=='M' and s.banks[i]==value for i in ais):continue
            cost+=min(meta[i]['load_ticks'] for i in ais)
            if value in produced and value not in s.backed:
                if not owners:raise ValueError('future batch input was lost')
                cost+=min(meta[i]['store_ticks'] for i,offset in owners)
        return cost
    def trim(candidates):
        nonlocal merged,pruned
        unique={}
        for s in candidates:
            k=(s.completed,s.cells,s.backed,s.banks);old=unique.get(k)
            if old is None or (s.cost,s.loads+s.stores)<(old.cost,old.loads+old.stores):unique[k]=s
        merged+=len(candidates)-len(unique)
        ranked=sorted(unique.values(),key=lambda s:(s.cost+bound(s),s.cost,s.loads+s.stores,repr(s.cells),repr(s.banks)))
        if width is not None:pruned+=max(0,len(ranked)-width);ranked=ranked[:width]
        return ranked
    def matrix(states,ai,members,needed):
        nonlocal expanded
        ns=[nodes[x] for x in members];first=ns[0];r=len(ns);active=states
        for ti,term in enumerate(first['terms']):
            more=[];av=[n['terms'][ti]['a'] for n in ns];bv=term['b']
            if any(n['terms'][ti]['b']!=bv for n in ns):raise ValueError('batch M cannot share distinct B records')
            for s in active:
                for sa,aa in ensure(s,ai,av,set(),needed):
                    reuse=sa.banks[ai]==bv
                    bs=[(sa,None)] if reuse else ensure(sa,ai,[bv],{aa},needed)
                    for sb,bb in bs:
                        banks=list(sb.banks);banks[ai]=bv;sb=replace(sb,banks=tuple(banks))
                        e={'op':'ROW_M_TERM','actor':names[ai],'native':members,'rows':r,'a':aa*8,
                           'b':None if reuse else bb*8,'a_records':av,'b_record':bv,'reuse_b':reuse,
                           'term':ti,'k':first['k'],'coefficient':term['coefficient'],'scale_shift':term['scale_shift'],'clear':ti==0}
                        try:more.append(emit(sb,[e]));expanded+=1
                        except ValueError as exc:
                            if str(exc)!='unmeasured row service shape or format':raise
            active=trim(more)
        more=[]
        for s in active:
            for ns,at in allocations(s,ai,set(),needed,r if masked else None):
                records=[n['output'] for n in [nodes[x] for x in members]]
                # Final writes are scalar SRAM transactions, one per row. The
                # same M accumulator is held until every row has its write ACK.
                events=[{'op':'ROW_M_FINAL','actor':names[ai],'native':members,'rows':r,'row':rr,
                    'address':at*8+rr,'record':value,'width':first['width'],'shift':first['shift'],'wait_s_ack':True}
                    for rr,value in enumerate(records)]
                entry=list(ns.cells[ai][at]);entry[:r]=records
                try:more.append(cell(emit(ns,events),ai,at,entry));expanded+=1
                except ValueError as exc:
                    if str(exc)!='unmeasured row service shape or format':raise
        return trim(more)
    def execute_unit(states,members,batchable,needed,*,serial_alternative):
        nonlocal expanded
        more=[];first=nodes[members[0]]
        for ai,a in enumerate(meta):
            if a['kind']!=first['kind']:continue
            if first['kind']=='M':
                if allow_batch and batchable and len(members)>1:more.extend(matrix(states,ai,members,needed))
                if serial_alternative or len(members)==1:
                    serial=states
                    for member in members:serial=matrix(serial,ai,[member],needed)
                    more.extend(serial)
            else:
                active=states
                for member in members:
                    n=nodes[member];prepared=[(s,()) for s in active]
                    for value in n['inputs']:
                        next_prepared=[]
                        for s,addresses in prepared:
                            for ns,at in ensure(s,ai,[value],set(addresses),needed):
                                next_prepared.append((ns,addresses+(at,)));expanded+=1
                        # Source addresses remain part of each open E command.
                        prepared=sorted(next_prepared,key=lambda x:(x[0].cost+bound(x[0]),x[0].cost,x[1]))
                        if width is not None:prepared=prepared[:width]
                    endings=[]
                    for s,addresses in prepared:
                        for ns,at in allocations(s,ai,set(),needed):
                            e={'op':'E','actor':names[ai],'native':member,'inputs':list(addresses),
                               'input_records':n['inputs'],'address':at,'record':n['output'],
                               'opcode':n['opcode'],'shift':n['shift'],'wait_s_ack':True}
                            endings.append(cell(emit(ns,[e]),ai,at,[n['output']]));expanded+=1
                    active=trim(endings)
                more.extend(active)
        return more
    def release(s,future):
        cells=tuple(tuple(tuple(x if x in future or x==ZERO else None for x in entry) for entry in row) for row in s.cells)
        return replace(s,cells=cells,backed=s.backed&future,banks=tuple(x if x in future else None for x in s.banks))
    initial=State(tuple(tuple((None,)*a['stride'] for _ in range(a['words']//a['stride'])) for a in meta),banks=(None,)*len(meta))
    states=[initial]
    if schedule=='fixed':
        for index,u in enumerate(groups):
            position=index;members=u['members'];future={value for value,at in last.items() if at>index}|live
            inputs={value for member in members for value in nodes[member]['inputs']}
            needed=future|inputs|{nodes[member]['output'] for member in members}
            more=execute_unit(states,members,u['batchable'],needed,serial_alternative=True)
            position=index+1;states=trim([release(s,future) for s in more])
            if not states:return {'status':'no_plan','unit':u['id'],'expanded':expanded}
    elif width==1:
        # Strict greedy makes ONE decision from its current physical state.
        # A width-one beam per completion-count layer would retain several
        # different-sized actions and is not this greedy control.
        while len(states[0].completed)<len(ready_graph.nodes):
            s=states[0];more=[]
            for members in ready_graph.actions(s.completed,allow_batch=allow_batch,policy=grouping_policy):
                done=s.completed|frozenset(members);future=ready_graph.future(done,live)
                inputs={value for member in members for value in nodes[member]['inputs']}
                needed=future|inputs|{nodes[member]['output'] for member in members}
                outcomes=execute_unit([s],list(members),len(members)>1,needed,serial_alternative=False)
                more.extend(release(replace(ns,completed=done),future) for ns in outcomes)
            states=trim(more)
            if not states:return {'status':'no_plan','expanded':expanded,'schedule':schedule}
    else:
        # Layers count completed native nodes, rather than command groups.
        # An r-row action advances by r and can meet a serial history at the
        # same layer only when the complete physical state also agrees.
        total=len(ready_graph.nodes);layers={0:states}
        for count in range(total):
            active=trim(layers.pop(count,[]))
            for s in active:
                for members in ready_graph.actions(s.completed,allow_batch=allow_batch,policy=grouping_policy):
                    done=s.completed|frozenset(members);future=ready_graph.future(done,live)
                    inputs={value for member in members for value in nodes[member]['inputs']}
                    needed=future|inputs|{nodes[member]['output'] for member in members}
                    more=execute_unit([s],list(members),len(members)>1,needed,serial_alternative=False)
                    for ns in more:layers.setdefault(len(done),[]).append(release(replace(ns,completed=done),future))
            # Trim once per destination layer after all histories at this
            # source count have contributed. This bounds retained memory,
            # while preserving distinct completed sets in the merge key.
            for dest in sorted(layers):layers[dest]=trim(layers[dest])
        states=trim(layers.get(total,[]))
        if not states:return {'status':'no_plan','expanded':expanded,'schedule':schedule}
    position=len(groups)
    for commit in graph['external_commits']:
        more=[];value=commit['record'];target=commit['external_address']
        for s in states:
            canonical=objects[value]['external_address']
            if target==canonical and value in s.backed:more.append(s);continue
            owners=locations(s,value)
            for ai,at,j in owners:more.append(store(s,ai,at,j,target=target,commit_for=commit['original_record']))
            if not owners:
                if value not in s.backed:raise ValueError('lost row live-out')
                for ai in range(len(names)):
                    for ns,at in ensure(s,ai,[value],set(),live):more.append(store(ns,ai,at,0,target=target,commit_for=commit['original_record']))
        states=trim(more)
    best=min(states,key=lambda s:(s.cost,s.loads+s.stores));events=[];h=best.history
    while h>=0:h,chunk=trail[h];events.append(chunk)
    events=[event for chunk in reversed(events) for event in chunk]
    return {'status':'planned','kind':'native-resident-row-program-v1','tile_sha256':digest(tile),
        'actors':actors,'zero_address':zero_address,'row_timing':row_timing,'scalar_timing':scalar_timing,
        'operand_contract':operand_contract,
        'events':events,'total_ticks':best.cost,'copy_ticks':best.copies,'native_service_ticks':best.cost-best.copies,
        'external_load_words':best.loads,'external_store_words':best.stores,'external_words':best.loads+best.stores,
        'width':width,'rank_policy':rank_policy,'allow_batch':allow_batch,'schedule':schedule,'grouping_policy':grouping_policy,
        'search_method':('strict_greedy' if width==1 else 'completion_layer_dp') if schedule=='ready' else 'fixed_order_frontier',
        'expanded':expanded,'merged':merged,'pruned':pruned,
        'scope':'bounded finite-S placement and paid layout search, serial native row services; no free cross-S gather, system or performance qualification'}
