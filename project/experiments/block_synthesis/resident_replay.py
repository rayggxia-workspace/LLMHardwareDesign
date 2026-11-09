"""Independent finite-S execution of resident_records event programs.

The observed-results dictionary is a verification log, never an operand source.
Every runtime operand comes from actual finite SRAM or a loaded M B bank.
"""


def replay(graph,plan,inputs,*,session=None,return_session=False):
    if plan.get('status')!='planned':raise ValueError('resident plan required')
    from native_reuse import KIND,Liveness,verify
    reuse_graph=graph.get('kind')==KIND
    liveness=None
    if reuse_graph:verify(graph);liveness=Liveness(graph)
    if bool(plan.get('value_reuse'))!=reuse_graph:raise ValueError('resident expression reuse contract differs')
    actors=plan['actors'];memory={name:[None]*a['words'] for name,a in actors.items()}
    tags={name:{} for name in actors};external={plan['zero_address']:0};external_tags={}
    observed={};logical_outputs={};banks={};pending={};position=0;copy_ticks=loads=stores=0;reused=0;recomputed=0
    from resident_transports import catalog,event_contract
    paths=catalog(plan.get('transports',()),actors);transfers=transfer_ticks=0;transport_nets=set()
    allowed_nets={n for p in paths.values() for n in p['nets']}
    if session is not None:
        if (session.get('actors')!=actors or not plan.get('initial_continuation') or
            set(session.get('memory',{}))!=set(actors) or
            any(len(session['memory'][n])!=a['words'] for n,a in actors.items())):
            raise ValueError('resident continuation needs a matching physical SRAM session')
        memory={n:list(words) for n,words in session['memory'].items()}
        tags={n:dict(row) for n,row in session['tags'].items()};banks=dict(session['banks'])
        transport_nets=set(session.get('transport_nets',()))
        if transport_nets!=set(plan['initial_continuation'].get('transport_nets',())):
            raise ValueError('resident transport nets have no matching predecessor')
    elif plan.get('initial_continuation') is not None:
        raise ValueError('resident warm program has no physical predecessor')
    def s16(value,i=0):
        v=(value>>(16*i))&65535
        return v-65536 if v>=32768 else v
    def read(actor,address):
        if not 0<=address<len(memory[actor]) or memory[actor][address] is None:
            raise ValueError('resident read outside written finite SRAM')
        return memory[actor][address]
    def write(actor,address,value,record=None):
        if not 0<=address<len(memory[actor]) or not 0<=value<1<<128:
            raise ValueError('resident write outside finite SRAM/word')
        memory[actor][address]=value
        if record is not None:tags[actor][address]=record
        else:tags[actor].pop(address,None)
    def require_record(actor,address,record):
        if tags[actor].get(address)!=record:raise ValueError('resident operand identity differs')
        return read(actor,address)
    for key,obj in graph['objects'].items():
        if obj['kind']=='produced':continue
        raw=obj['literal'] if 'literal' in obj else inputs[(obj['tensor'],obj['index'])]
        if type(raw)!=int or not -(1<<31)<=raw<1<<31:raise ValueError('initial resident S32 record out of range')
        word=raw&0xffffffff;address=obj['external_address']
        if address in external and external[address]!=word:raise ValueError('conflicting initial external records')
        external[address]=word;external_tags.setdefault(address,set()).add(key)
    identities={key:('constant',o['literal'],o['external_address']) if o['kind']=='constant' else
                ('external',o['tensor'],o['index'],o['external_address'],o['bits'])
                for key,o in graph['objects'].items() if o['kind']!='produced'}
    persistent=set(plan.get('persistent_records',()))
    if not persistent<=identities.keys():raise ValueError('resident persistent identity is not read-only')
    def check_continuation(contract,previous=False):
        if contract.get('kind')!='resident-readonly-continuation-v1' or set(contract.get('actors',{}))!=set(actors):
            raise ValueError('resident continuation actor contract differs')
        for name,a in actors.items():
            row=contract['actors'][name]
            if len(row['slots'])!=a['words']//a['stride']:raise ValueError('resident continuation cell extent differs')
            for at,key in enumerate(row['slots']):
                if key is None:continue
                if key not in persistent or key not in identities:raise ValueError('resident continuation has a transient record')
                if previous and session['identities'].get(key)!=identities[key]:
                    raise ValueError('resident persistent source identity changed across iterations')
                word=require_record(name,at*a['stride'],key)
                if word!=external[graph['objects'][key]['external_address']]:
                    raise ValueError('resident persistent SRAM value changed')
            for cell in row['padding']:
                if a['kind']!='M' or type(cell)!=int or not 0<=cell<len(row['slots']):
                    raise ValueError('resident continuation padding extent differs')
                if any(read(name,8*cell+i)!=0 for i in range(1,8)):
                    raise ValueError('resident persistent padding changed')
            key=row['bank']
            if key is not None:
                if (a['kind']!='M' or key not in persistent or key not in identities or name not in banks or
                    banks[name]!=(key,external[graph['objects'][key]['external_address']])):
                    raise ValueError('resident persistent B bank differs')
                if previous and session['identities'].get(key)!=identities[key]:
                    raise ValueError('resident B source identity changed across iterations')
    if session is not None:
        check_continuation(plan['initial_continuation'],previous=True)
        # Stale transient labels from a prior element are not current SSA
        # values, even if their numeric slot IDs happen to have the same text.
        for name,a in actors.items():
            row=plan['initial_continuation']['actors'][name]
            tags[name]={i*a['stride']:key for i,key in enumerate(row['slots']) if key is not None}
        banks={name:banks[name] for name in actors if plan['initial_continuation']['actors'][name]['bank'] is not None}
    for event in plan['events']:
        kind=event['op'];actor=event['actor'];a=actors[actor]
        if kind in ('LOAD','LOAD_ZERO'):
            if event.get('wait_ack') is not True:raise ValueError('resident LOAD missing ACK')
            at=event['external_address']
            if at not in external:raise ValueError('resident LOAD before external STORE ACK')
            record=event.get('record')
            if kind=='LOAD_ZERO':
                if at!=plan['zero_address'] or external[at]!=0:raise ValueError('padding is not explicit zero')
            elif record not in external_tags.get(at,set()):raise ValueError('resident external object identity differs')
            write(actor,event['address'],external[at],record)
            copy_ticks+=a['load_ticks'];loads+=1
        elif kind in ('STORE','STORE_COMMIT'):
            if event.get('wait_ack') is not True:raise ValueError('resident STORE missing ACK')
            record=event['record'];word=require_record(actor,event['address'],record)
            at=graph['objects'][record]['external_address']
            if kind=='STORE_COMMIT':
                candidates=[c for c in graph.get('external_commits',()) if c['original_record']==event.get('commit_for') and c['record']==record]
                if not reuse_graph or len(candidates)!=1:raise ValueError('resident original output commit differs')
                at=candidates[0]['external_address']
            if at!=event['external_address']:raise ValueError('resident STORE external address differs')
            external[at]=word;external_tags[at]={record};copy_ticks+=a['store_ticks'];stores+=1
        elif kind=='TRANSFER':
            p=event_contract(event,paths,actors)
            word=require_record(p['source'],event['source_address'],event['record'])
            write(actor,event['address'],word,event['record'])
            # The serial event finishes only after the destination write ACK;
            # no external backing is created and the source remains intact.
            copy_ticks+=p['ticks'];transfers+=1;transfer_ticks+=p['ticks'];transport_nets.update(p['nets'])
        elif kind=='DISCARD':
            if (not liveness or pending and graph['operations'][position]['kind']!='M' or
                event.get('reason')!='recompute-before-next-use' or not liveness.may_discard(position,event['record'])):
                raise ValueError('unsafe native recomputation discard')
            require_record(actor,event['address'],event['record']);tags[actor].pop(event['address'])
        else:
            if position>=len(graph['operations']):raise ValueError('extra resident native operation')
            n=graph['operations'][position]
            if event['native']!=n['id'] or kind!='REUSE' and a['kind']!=n['kind']:raise ValueError('resident native order/actor differs')
            if kind=='REUSE':
                if not reuse_graph or pending or n.get('reuse_of')!=event['record'] or event['record']!=n['output']:
                    raise ValueError('resident reuse point/record differs')
                if event.get('where')=='S':word=require_record(actor,event['address'],n['output'])
                elif event.get('where')=='external':
                    at=graph['objects'][n['output']]['external_address']
                    if event.get('external_address')!=at or n['output'] not in external_tags.get(at,set()):
                        raise ValueError('resident reuse has no acknowledged external backing')
                    word=external[at]
                else:raise ValueError('resident reuse source differs')
                if n['output'] not in observed or word!=observed[n['output']]:raise ValueError('resident reused value differs')
                logical_outputs[n['id']]=word;position+=1;reused+=1
            elif kind=='M_TERM':
                old=pending.get(actor);ti=old[1] if old else 0
                if ti>=len(n['terms']):raise ValueError('too many native M terms')
                t=n['terms'][ti]
                if (event['coefficient'],event['scale_shift'],event['k'],event['clear'])!=(
                        t['coefficient'],t['scale_shift'],n['k'],ti==0):raise ValueError('native M term encoding differs')
                if event['a_record']!=t['a'] or event['b_record']!=t['b']:raise ValueError('native M record differs')
                av=require_record(actor,event['a'],t['a'])
                for i in range(1,4):
                    if read(actor,event['a']+i)!=0:raise ValueError('native A padding changed')
                if event['reuse_b']:
                    if actor not in banks or banks[actor][0]!=t['b']:raise ValueError('native B reuse without matching bank')
                    bv=banks[actor][1]
                else:
                    bv=require_record(actor,event['b'],t['b'])
                    for i in range(1,8):
                        if read(actor,event['b']+i)!=0:raise ValueError('native B padding changed')
                    banks[actor]=(t['b'],bv)
                acc=old[2] if old else 0
                acc+=sum(s16(av,i)*s16(bv,i) for i in range(n['k']))*t['coefficient']*(1<<t['scale_shift'])
                if not -(1<<63)<=acc<1<<63:raise ValueError('resident native S64 partial overflow')
                pending[actor]=(n['id'],ti+1,acc)
            elif kind=='M_FINAL':
                if actor not in pending or pending[actor][:2]!=(n['id'],len(n['terms'])):
                    raise ValueError('native M final before all terms')
                if (event['width'],event['shift'])!=(n['width'],n['shift']):raise ValueError('native M final encoding differs')
                acc=pending.pop(actor)[2];shift=n['shift']
                if shift:
                    q,r=divmod(acc,1<<shift);acc=q+int(2*r>1<<shift or (2*r==1<<shift and q%2))
                acc=max(-(1<<(n['width']-1)),min((1<<(n['width']-1))-1,acc));word=acc&0xffffffff
                if event.get('wait_s_ack') is not True:raise ValueError('native final missing SRAM ACK')
                if event['record']!=n['output']:raise ValueError('native final output differs')
                if n.get('reuse_of'):
                    if word!=observed[n['output']]:raise ValueError('native recomputed expression differs')
                    recomputed+=1
                write(actor,event['address'],word,n['output']);observed[n['output']]=word
                logical_outputs[n['id']]=word;position+=1
            elif kind=='E':
                if pending or event['opcode']!=n['opcode'] or event['shift']!=n['shift']:
                    raise ValueError('native E command/context differs')
                if event['input_records']!=n['inputs'] or len(event['inputs'])!=len(n['inputs']):
                    raise ValueError('native E operands differ')
                args=[require_record(actor,address,record) for address,record in zip(event['inputs'],n['inputs'])]
                word=0
                for i in range(8):
                    v=[s16(x,i) for x in args]
                    if n['opcode']==5:value=min(v)
                    elif n['opcode']==6:value=v[0] if v[2] else v[1]
                    else:raise ValueError('unsupported resident E opcode')
                    word|=(value&65535)<<(16*i)
                if event.get('wait_s_ack') is not True or event['record']!=n['output']:
                    raise ValueError('native E output/ACK differs')
                if n.get('reuse_of'):
                    if word!=observed[n['output']]:raise ValueError('native recomputed expression differs')
                    recomputed+=1
                write(actor,event['address'],word,n['output']);observed[n['output']]=word
                logical_outputs[n['id']]=word;position+=1
            else:raise ValueError('unknown resident event')
    if position!=len(graph['operations']) or pending:raise ValueError('resident native program incomplete')
    commits=graph['external_commits'] if reuse_graph else [
        {'record':r,'external_address':graph['objects'][r]['external_address']} for r in graph['live_out'].values()]
    for commit in commits:
        record=commit['record'];address=commit['external_address']
        if record not in external_tags.get(address,set()) or external[address]!=observed[record]:
            raise ValueError('resident live output not externally committed')
    if (copy_ticks,loads,stores,loads+stores)!=(plan['copy_ticks'],plan['external_load_words'],
            plan['external_store_words'],plan['external_words']):raise ValueError('resident copy accounting differs')
    if 'continuation' in plan:check_continuation(plan['continuation'])
    if paths and ((transfers,transfer_ticks,sorted(transport_nets))!=(
            plan['transport_words'],plan['transport_ticks'],plan['transport_nets']) or
            not transport_nets<=allowed_nets or
            plan.get('transport_net_budget') is not None and len(transport_nets)>plan['transport_net_budget'] or
            plan.get('continuation',{}).get('transport_nets')!=sorted(transport_nets)):
        raise ValueError('resident transport/static net accounting differs')
    result={'passed':True,'observed_native_outputs':observed,'copy_ticks':copy_ticks,
            'external_words':loads+stores,'native_operations':position,
            'scope':'independent finite-S and external ACK interpreter; not RTL/SystemC/time or energy qualification'}
    if reuse_graph:
        if (reused,recomputed)!=(plan.get('reused_operations'),plan.get('recomputed_duplicate_operations')):
            raise ValueError('resident executed/reused work accounting differs')
        result.update(logical_native_outputs=logical_outputs,reused_operations=reused,recomputed_duplicate_operations=recomputed)
    if return_session:
        result['session']={'actors':actors,'memory':memory,'tags':tags,'banks':banks,'identities':identities,
                           'transport_nets':sorted(transport_nets)}
    return result
