"""Independent finite-S execution of resident_records event programs.

The observed-results dictionary is a verification log, never an operand source.
Every runtime operand comes from actual finite SRAM or a loaded M B bank.
"""


def replay(graph,plan,inputs):
    if plan.get('status')!='planned':raise ValueError('resident plan required')
    actors=plan['actors'];memory={name:[None]*a['words'] for name,a in actors.items()}
    tags={name:{} for name in actors};external={plan['zero_address']:0};external_tags={}
    observed={};banks={};pending={};position=0;copy_ticks=loads=stores=0
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
        elif kind=='STORE':
            if event.get('wait_ack') is not True:raise ValueError('resident STORE missing ACK')
            record=event['record'];word=require_record(actor,event['address'],record)
            at=graph['objects'][record]['external_address']
            if at!=event['external_address']:raise ValueError('resident STORE external address differs')
            external[at]=word;external_tags[at]={record};copy_ticks+=a['store_ticks'];stores+=1
        else:
            if position>=len(graph['operations']):raise ValueError('extra resident native operation')
            n=graph['operations'][position]
            if event['native']!=n['id'] or a['kind']!=n['kind']:raise ValueError('resident native order/actor differs')
            if kind=='M_TERM':
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
                write(actor,event['address'],word,n['output']);observed[n['output']]=word;position+=1
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
                write(actor,event['address'],word,n['output']);observed[n['output']]=word;position+=1
            else:raise ValueError('unknown resident event')
    if position!=len(graph['operations']) or pending:raise ValueError('resident native program incomplete')
    for record in graph['live_out'].values():
        address=graph['objects'][record]['external_address']
        if record not in external_tags.get(address,set()) or external[address]!=observed[record]:
            raise ValueError('resident live output not externally committed')
    if (copy_ticks,loads,stores,loads+stores)!=(plan['copy_ticks'],plan['external_load_words'],
            plan['external_store_words'],plan['external_words']):raise ValueError('resident copy accounting differs')
    return {'passed':True,'observed_native_outputs':observed,'copy_ticks':copy_ticks,
            'external_words':loads+stores,'native_operations':position,
            'scope':'independent finite-S and external ACK interpreter; not RTL/SystemC/time or energy qualification'}
