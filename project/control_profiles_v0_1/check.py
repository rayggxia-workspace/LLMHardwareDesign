"""Independent immutable-trace replay. Does not produce Model inputs/actions."""
import copy,hashlib
import images
codec=images.codec; need=images.need


def verify(report,files,kinds,expected):
    parsed={n:images.parse(b,kinds.get(int(n[5:])) if n!='mother' else None) for n,b in files.items()}
    regs={n:[0]*8 for n in files}; pcs={n:0 for n in files}; taskargs={}; taskseq={}; global_credit={}; objects=set(); valid=set()
    tokens={}; memory={}; pm={}; fetched={}; desc_reads={n:set() for n in files}; held={}; accepted_commands={}; effects={}; response=set(); local_terminals={}
    state=None; params=None; source_done=False; ack=done=0; shadow=None; initial=None; first_fault=False; fault_tick=None; fault_index=None; publication=False; replay=False
    local_prefix={}; parameter_reads={}; parameter_loaded=set(); input_data=None; state_reads={}
    operations=0; retired=0; branch=loop=0; prefix_read=prefix_write=0; last_tick=-1
    for index,e in enumerate(report['trace']):
        t=e['tick']; k=e['kind']; n=e.get('cpu'); need(t>=last_tick,'trace tick order'); last_tick=t
        if k=='BEGIN':
            need(index==0,'single BEGIN'); params=e['parameters']; initial=copy.deepcopy(e['initial']); state=copy.deepcopy(initial)
            need(state['root']>0 and state['store'].get(state['root']) not in (None,0),'nonzero state evidence'); input_data=bytes.fromhex(e['input_data'])
            expected_sequences=expected.get('initial_sequences',{b:0 for b in kinds}); need(e['initial_task_sequences']==expected_sequences,'initial controller sequence provenance')
            taskseq={'local'+str(b):v for b,v in expected_sequences.items()}
        elif k=='PM_REQ':
            need(n not in pm and 0<=e['address']<=len(files[n])-16 and e['address']%16==0,'single bounded PM request')
            pm[n]=e
        elif k=='PM_RSP':
            need(n in pm and pm[n]['tick']<t and pm[n]['address']==e['address'] and bytes.fromhex(e['data'])==files[n][e['address']:e['address']+16],'actual PM stored data association')
            desc_reads[n].add(e['address']); pm.pop(n)
        elif k=='FETCH':
            need(e['pc']==pcs[n] and n not in fetched and 128+e['pc']*16 in desc_reads[n] and int(e['word'],16)==parsed[n]['records']['instruction'][e['pc']],'binary PC fetch provenance')
            fetched[n]=int(e['word'],16)
        elif k=='OFFER':
            need(e['channel'] not in held,'bounded channel duplicate offer'); held[e['channel']]=dict(e,observation_index=index)
            if e['action']=='host': need(not taskargs and not objects and not tokens and not pm and all(c['done'] for c in global_credit.values()),'host offer before actual drain')
        elif k=='SAMPLE':
            need(e['channel'] in held and e['payload']==held[e['channel']]['payload'],'held payload changed')
        elif k=='ACCEPT':
            channel=e['channel']; need(channel in held and held[channel]['tick']<t and e['payload']==held[channel]['payload'],'whole message accept/hold')
            offered=held.pop(channel); action=e['action']; p=e['payload']
            if action=='param':
                ins=codec.decode_instruction(fetched['mother'],'mother'); need(ins['op']=='G_PARAM' and p['index']==ins['x'] and int.from_bytes(bytes.fromhex(p['data']),'little')==params[ins['x']],'G_PARAM actual immutable word')
                regs['mother'][ins['a']]=params[ins['x']]
            elif action=='call':
                m=codec.unpack_record('task_message',bytes.fromhex(p['hex'])); b=m['target_block']; child='local'+str(b)
                ins=codec.decode_instruction(fetched['mother'],'mother'); need(ins['op']=='G_CALL' and b==ins['a'] and m['completion_token']==ins['b'] and m['task_descriptor']==ins['c'],'CALL selected fields')
                need(m['completion_token'] not in global_credit and len(global_credit)<2 and child not in taskargs,'finite global reservation')
                need([m['arg'+str(i)] for i in range(8)]==regs['mother'] and m['task_sequence']==taskseq.get(child,0)+1,'immutable CALL register snapshot/sequence')
                taskseq[child]=m['task_sequence']; taskargs[child]=[m['arg'+str(i)] for i in range(8)]; regs[child]=[0]*8; local_prefix[child]=[0,0]
                pcs[child]=parsed[child]['records']['task'][m['task_descriptor']]['entry_pc']; global_credit[m['completion_token']]=dict(cpu=child,done=False)
            elif action=='command':
                child=channel[4:]; need(child in taskargs and child in fetched and child in objects and child not in tokens,'service owned CALL/object/IREG')
                ins=codec.decode_instruction(fetched[child],'local'); d=codec.unpack_record('execution',bytes.fromhex(p['descriptor']))
                offset=parsed[child]['header']['execution_offset']+128*ins['c']
                need(ins['op']=='L_EXEC' and all(offset+i in desc_reads[child] for i in range(0,128,16)) and
                    d==parsed[child]['records']['execution'][ins['c']] and d['resource']==ins['a'],'actual full descriptor read/EXEC')
                need(d['src0']==255 or child in valid,'read before actual service ACK/WAIT')
                need(p['args']==taskargs[child] and p['job']==e['job'] and p['epoch']==e['epoch'] and p['task_sequence']==taskseq[child],'service namespace/arguments')
                tokens[child]=p['operation']; accepted_commands[p['operation']]=dict(cpu=child,descriptor=d,tick=t,offered=offered['tick'],offered_index=offered['observation_index'],args=p['args']); operations+=1
            elif action=='response':
                op=p['operation']; need(op in accepted_commands and op not in response,'duplicate/unowned actual response')
                c=accepted_commands[op]; child=c['cpu']; d=c['descriptor']; need(tokens.get(child)==op,'response token ownership')
                if p['write_bytes']: need(op in effects and effects[op]['tick']<t,'confirmed write before actual store')
                need(p['read_bytes']==p['write_bytes'] and p['write_bytes'] in (0,16),'candidate prefix byte count')
                response.add(op)
                local_prefix[child][0]+=p['read_bytes']; local_prefix[child][1]+=p['write_bytes']
                if d['native0']==2 and p['status']==0: ack|=d['native1']
            elif action=='terminal':
                m=codec.unpack_record('event_message',bytes.fromhex(p['hex'])); child='local'+str(m['source_block']); tok=m['completion_token']
                need(child in taskargs and child not in objects and child not in tokens and child not in pm and tok in global_credit and not global_credit[tok]['done'],'terminal before actual obligations')
                need(m['task_sequence']==taskseq[child] and global_credit[tok]['cpu']==child and m['job_id']==e['job'] and m['epoch']==e['epoch'],'terminal namespace')
                need([m['confirmed_read_bytes'],m['confirmed_write_bytes']]==local_prefix[child],'child confirmed prefix from actual responses')
                global_credit[tok]['done']=True; taskargs.pop(child); fetched.pop(child,None); prefix_read+=m['confirmed_read_bytes']; prefix_write+=m['confirmed_write_bytes']
                if m['status']: first_fault=True; fault_tick=t if fault_tick is None else fault_tick; fault_index=index if fault_index is None else fault_index
                else:
                    ds=[x['descriptor'] for x in accepted_commands.values() if x['cpu']==child and x['tick']>local_terminals.get(child,-1)]
                    if any(d['native0']==1 for d in ds): source_done=True
                    for d in ds:
                        if d['native0']==2: done|=d['native1']
                local_terminals[child]=t
            elif action=='cancel':
                m=codec.unpack_record('task_message',bytes.fromhex(p['hex'])); child='local'+str(m['target_block'])
                need(first_fault and child in taskargs and m['kind']==1 and m['task_sequence']==taskseq[child] and all(m['arg'+str(i)]==0 for i in range(8)),'CANCEL ownership/identity')
            elif action=='host':
                need(not taskargs and not objects and not tokens and not pm and all(c['done'] for c in global_credit.values()),'host terminal before closed execution/PM')
                need(p['read_bytes']==prefix_read and p['write_bytes']==prefix_write,'global confirmed prefix from actual terminals')
                need(p['status']==expected.get('status',0),'unexpected host status')
            else: need(False,'unknown accepted action')
        elif k=='RETIRE':
            word=int(e['word'],16); need(n in fetched and fetched[n]==word and e['pc']==pcs[n],'retirement actual fetched word/PC')
            ins=codec.decode_instruction(word,'mother' if n=='mother' else 'local'); op=ins['op']; next_pc=pcs[n]+1
            if op in ('G_MOVI','L_MOVI'): regs[n][ins['a']]=ins['x']
            elif op=='L_ARG': regs[n][ins['a']]=taskargs[n][ins['b']]
            elif op=='L_ADDI':
                delta=ins['x']-2**32 if ins['x']>=2**31 else ins['x']; v=regs[n][ins['a']]+delta; need(0<=v<2**32,'retired arithmetic overflow'); regs[n][ins['a']]=v
            elif op in ('G_LOOP','L_LOOP'):
                need(regs[n][ins['a']]>0 and ins['x']<pcs[n],'loop legality'); regs[n][ins['a']]-=1; next_pc=ins['x'] if regs[n][ins['a']] else next_pc; loop+=1
            elif op in ('G_BRANCH','L_BRANCH'):
                need(all(pcs[n]<v<len(parsed[n]['program']) for v in (ins['x'],ins['y'])),'forward branch'); next_pc=ins['x'] if regs[n][ins['a']] else ins['y']; branch+=1
            elif op=='L_WAIT':
                need(n in tokens and tokens[n] in response,'WAIT before response'); tokens.pop(n); valid.add(n)
            elif op=='G_WAIT':
                selected=[x for x in range(32) if ins['x']&(1<<x)]; need(selected and all(x in global_credit and global_credit[x]['done'] for x in selected),'G_WAIT before actual child terminals')
                for x in selected: global_credit.pop(x)
            need(e['registers']==regs[n] and e['next_pc']==next_pc,'retirement scalar/branch semantics')
            pcs[n]=next_pc; fetched.pop(n); retired+=1
        elif k=='OPEN': need(n not in objects,'duplicate OPEN'); objects.add(n); valid.discard(n)
        elif k=='DROP': need(n in objects and n not in tokens,'DROP before token drain'); objects.remove(n); valid.discard(n)
        elif k=='S_WRITE':
            op=e['operation']; need(op in accepted_commands and op not in effects and accepted_commands[op]['tick']<t,'actual scratch write ownership')
            c=accepted_commands[op]; d=c['descriptor']; source=memory[n] if d['src0']==0 else input_data
            if d['native0'] in (1,4): need(op in state_reads,'compute without actual old/next read'); source=state_reads[op]
            need(e['input_sha256']==images.sha(source),'scratch input version provenance')
            wanted=hashlib.sha256(source+bytes([d['resource']])+op.to_bytes(4,'little')+e['job'].to_bytes(4,'little')).digest()[:16]
            need(bytes.fromhex(e['data'])==wanted,'opaque service version token')
            need(not d['native0'] or op in parameter_loaded,'state action before actual parameter response')
            effects[op]=e; memory[n]=wanted
        elif k=='NEXT_WRITE':
            need(e['operation'] in accepted_commands and accepted_commands[e['operation']]['descriptor']['native0']==1 and e['operation'] in parameter_loaded,'next without owned R update/parameters')
            c=accepted_commands[e['operation']]; need(e['operation'] in state_reads,'update before actual committed read')
            data=hashlib.sha256(state_reads[e['operation']]+bytes([c['descriptor']['resource']])+e['operation'].to_bytes(4,'little')+e['job'].to_bytes(4,'little')).digest()[:16]
            need(e['payload']==int.from_bytes(data[:4],'little'),'next version depends on actual nonzero old payload')
            need(e['old']==state['root'] and e['generation']==state['generation'] and e['handle']!=e['old'] and e['handle']>0,'next may not alias committed old')
            shadow=e
        elif k=='PUBLISH':
            need(e['operation'] in accepted_commands and accepted_commands[e['operation']]['descriptor']['native0']==3 and e['operation'] in parameter_loaded,'publication lacks owned candidate command/parameters')
            owed=not first_fault or accepted_commands[e['operation']]['offered_index']<fault_index
            need(shadow is not None and source_done and ack&params[3]==params[3] and done&params[3]==params[3] and owed,'publication before all actual obligations')
            need(e['old']==state['root'] and e['new']==params[1] and e['generation']==state['generation']+1 and e['transaction']==params[4],'atomic state publication tuple')
            state['root']=e['new']; state['generation']=e['generation']; publication=True
        elif k=='PUBLISH_REPLAY':
            need(e['operation'] in accepted_commands and accepted_commands[e['operation']]['descriptor']['native0']==3 and e['operation'] in parameter_loaded,'replay lacks owned publication/parameters')
            row=initial['journal'].get(e['transaction']); need(row is not None and (row['old'],row['new'],row['generation'])==(e['old'],e['new'],e['generation']),'replay lacks committed journal'); replay=True
        elif k in ('OLD_READ','NEXT_READ'):
            op=e['operation']; need(op in accepted_commands and op in parameter_loaded and op not in state_reads,'state read ownership/parameters')
            d=accepted_commands[op]['descriptor']; wanted=state['store'][state['root']].to_bytes(4,'little')*4 if k=='OLD_READ' else shadow['payload'].to_bytes(4,'little')*4 if shadow else None
            need(d['native0']==(1 if k=='OLD_READ' else 4) and e['handle']==(state['root'] if k=='OLD_READ' else params[1]) and bytes.fromhex(e['data'])==wanted,'actual old/next payload/handle')
            if k=='NEXT_READ': need(source_done,'next read before producer terminal')
            state_reads[op]=bytes.fromhex(e['data'])
        elif k=='TRAP': first_fault=True; fault_tick=t if fault_tick is None else fault_tick; fault_index=index if fault_index is None else fault_index; fetched.pop(n,None)
        elif k=='HOST_CANCEL': first_fault=True; fault_tick=t if fault_tick is None else fault_tick; fault_index=index if fault_index is None else fault_index
        elif k=='CANCEL': need(first_fault and n in taskargs and e['pc']==pcs[n],'cancel observation after identity-checked message')
        elif k=='CANCEL_TOKEN': need(n in tokens and tokens[n] in response,'cancel cleanup before actual response'); tokens.pop(n)
        elif k=='POISON': need(expected.get('poison') and (tokens or held or pm) and not report['outcome'],'poison lost obligations/host result')
        elif k=='PARAM_REQ':
            need(n in tokens and n not in parameter_reads and e['reference']==4096 and e['bytes']==32,'parameter request ownership/extent'); parameter_reads[n]=e
        elif k=='PARAM_RSP':
            need(n in parameter_reads and parameter_reads[n]['tick']<t and bytes.fromhex(e['data'])==b''.join(v.to_bytes(4,'little') for v in params),'actual immutable parameter response')
            parameter_reads.pop(n); parameter_loaded.add(tokens[n])
        elif k in ('CONTROL_REJECT','SERVICE_REJECT'): pass
        else: need(False,'unknown observation kind '+k)
    need(report['poison']==bool(expected.get('poison')),'poison scenario expectation')
    need(report['state']['root']==expected.get('root',initial['root']) and report['state']['generation']==expected.get('generation',initial['generation']),'state root/generation expected')
    if expected.get('services') is not None: need(operations==expected['services'],'independent profile service count')
    need((publication or replay)==bool(expected.get('published')),'publication/replay expectation')
    if not report['poison']: need(not held and not taskargs and not objects and not tokens and not pm,'unclosed finite boundary')
    return dict(retired=retired,services=operations,branches=branch,loops=loop,published=publication,replayed=replay,rtl_tested=False)


def mutations(report,files,kinds,expected):
    result=[]
    for name in ['commit_before_consumers','wrong_ARG_value','terminal_before_wait','changed_held_packet']:
        r=copy.deepcopy(report)
        if name=='commit_before_consumers':
            commit=next(e for e in r['trace'] if e['kind']=='PUBLISH'); r['trace'].remove(commit)
            pos=next(i for i,e in enumerate(r['trace']) if e['kind']=='NEXT_WRITE')+1; commit['tick']=r['trace'][pos-1]['tick']; r['trace'].insert(pos,commit)
        elif name=='wrong_ARG_value': next(e for e in r['trace'] if e['kind']=='RETIRE' and images.codec.decode_instruction(int(e['word'],16),'mother' if e['cpu']=='mother' else 'local')['op']=='L_ARG')['registers'][0]^=1
        elif name=='terminal_before_wait':
            e=next(e for e in r['trace'] if e['kind']=='RETIRE' and e['cpu']=='local0' and images.codec.decode_instruction(int(e['word'],16),'local')['op']=='L_WAIT'); r['trace'].remove(e)
        else: next(e for e in r['trace'] if e['kind']=='SAMPLE' and not e['ready'])['payload']={}
        try: verify(r,files,kinds,expected)
        except (ValueError,KeyError,StopIteration): result.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted profile mutation '+name)
    return result
