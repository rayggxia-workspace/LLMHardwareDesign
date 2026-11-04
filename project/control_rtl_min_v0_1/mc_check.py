"""Independent mother architectural/credit observer, never a signal generator."""
import copy,json,pathlib
import run as common
codec=common.codec; image=common.check_cycles.image
need=common.check_cycles.need
HERE=pathlib.Path(__file__).resolve().parent
PINS=json.loads((HERE/'mc_pins.json').read_text(encoding='utf-8'))['pins']


def decode(log):
    rows=[]
    for line in log.splitlines():
        if not line.startswith('C '): continue
        _,t,value=line.split(); need(not any(c in value.lower() for c in 'xz'),'mother unknown sample')
        value=int(value,16); s={}
        for p in reversed(PINS): s[p['name']]=value&((1<<p['width'])-1); value>>=p['width']
        need(value==0,'mother sample width'); rows.append(dict(cycle=int(t),signals=s))
    return rows


def check(rows,case):
    shadow=bytearray([0xcd]*4736); cfg=pm=ireg=job=None
    held={}; generation=total=written=readback=0; ids=[]; header=None; prepared=authorized=False
    release_epoch=0; contexts={}; regs=[0]*8; next_seq={0:0,1:0}; ready={}; consumed=set(); bind_words={}
    pending=None; first_error=None; starts=calls=cancels=results=ready_received=0
    prefix_read=prefix_write=0; saturation=False; last_start=0; poison_seen=False; stall_age=0; retired=[]
    start_fields=['start_job_i','start_epoch_i','start_sequence_i','start_generation_i','start_args_i']
    cfg_fields=[p['name'] for p in PINS if p['name'].startswith('cfg_req_') and p['name'] not in ['cfg_req_valid_i','cfg_req_ready_o']]
    result_fields=[p['name'] for p in PINS if p['name'].startswith('result_') and p['name'] not in ['result_valid_o','result_ready_i']]
    channels=[('cfg_req_valid_i','cfg_req_ready_o',cfg_fields),('cfg_rsp_valid_o','cfg_rsp_ready_i',['cfg_rsp_status_o','cfg_rsp_data_o','cfg_rsp_generation_o']),
        ('pm_req_valid_o','pm_req_ready_i',['pm_req_write_o','pm_req_address_o','pm_req_data_o','trace_pm_owner_o']),
        ('pm_rsp_valid_i','pm_rsp_ready_o',['pm_rsp_data_i','pm_rsp_error_i']),('start_valid_i','start_ready_o',start_fields),
        ('task_valid_o','task_ready_i',['task_packet_o','task_target_o','task_credit_o']),
        ('return_valid_i','return_ready_o',['return_packet_i']),('result_valid_o','result_ready_i',result_fields)]
    def ctrl_fault(status,pc):
        nonlocal first_error,ireg
        if first_error is None: first_error=dict(status=status,pc=pc,source=255,child_pc=0xffffffff,task=0)
        ireg=None
    for index,row in enumerate(rows):
        t=row['cycle']; s=row['signals']; need(t==index,'mother cycle index')
        if not s['rst_ni']:
            need(not any(s[n] for n in ['cfg_req_ready_o','cfg_rsp_valid_o','pm_req_valid_o','start_ready_o','task_valid_o','result_valid_o']),
                 'mother reset valid/admission')
            cfg=pm=ireg=job=None; held={}; prepared=authorized=False; generation=written=readback=0
            contexts={}; ready={}; pending=None; first_error=None; consumed=set(); next_seq={0:0,1:0}; stall_age=0
            continue
        for valid,rdy,payload in channels:
            value=tuple(s[n] for n in payload)
            if valid in held: need(s[valid] and value==held[valid],'mother held tuple '+valid)
            if s[valid] and not s[rdy]: held[valid]=value
            else: held.pop(valid,None)
        cf=s['cfg_req_valid_i'] and s['cfg_req_ready_o']; mf=s['pm_req_valid_o'] and s['pm_req_ready_i']
        mr=s['pm_rsp_valid_i'] and s['pm_rsp_ready_o']; sf=s['start_valid_i'] and s['start_ready_o']
        tf=s['task_valid_o'] and s['task_ready_i']; rf=s['return_valid_i'] and s['return_ready_o']; ef=s['result_valid_o'] and s['result_ready_i']
        # Install an observed first offer as a reserved, still unaccepted, CALL.
        if s['task_valid_o'] and pending is None:
            m=codec.unpack_record('task_message',s['task_packet_o'].to_bytes(64,'little')); b=m['target_block']
            need(job is not None and b in (0,1) and s['task_target_o']==b,'mother output target/ownership')
            if m['kind']==0:
                need(ireg is not None and ireg['word']>>120==0x10 and first_error is None and b not in contexts,'new CALL after fault/overlap')
                ins=codec.decode_instruction(ireg['word'],'mother'); token=ins['b']
                need(token<8 and token not in [c['token'] for c in contexts.values()] and job['enabled']&(1<<b),'CALL reservation capacity')
                need(all(header['event_binding_offset']+16*i in bind_words for i in range(header['event_binding_count'])),'CALL before actual binding loads')
                next_seq[b]+=1
                expected=dict(kind=0,target_block=b,job_id=job['job'],epoch=job['epoch'],task_sequence=next_seq[b],completion_token=token,
                    task_descriptor=ins['c'],program_image_id=job['ids'][b],topology_id=header['topology_id'])
                expected.update({'arg'+str(i):regs[i] for i in range(8)})
                packet=codec.pack_record('task_message',expected)
                need(s['task_packet_o']==int.from_bytes(packet,'little') and s['task_credit_o']==1,'full CALL immutable args/identity snapshot')
                contexts[b]=dict(token=token,packet=m,word=s['task_packet_o'],accepted=None,terminal=None,cancel=False)
            else:
                need(first_error is not None and b in contexts and contexts[b]['accepted'] is not None and contexts[b]['terminal'] is None,
                     'CANCEL before accepted CALL/after terminal')
                c=contexts[b]; expected=dict(c['packet']); expected['kind']=1
                for i in range(8): expected['arg'+str(i)]=0
                need(s['task_packet_o']==int.from_bytes(codec.pack_record('task_message',expected),'little') and not s['task_credit_o'],'full CANCEL snapshot/credit')
            pending=dict(block=b,kind=m['kind'],word=s['task_packet_o'])
        if s['result_valid_o'] and first_error is not None:
            need(pending is None and pm is None and all(c['terminal'] is not None for c in contexts.values()),'error result before accepted child terminals')
            contexts={}; ready={}; ireg=None
        if s['trace_aborting_o']:
            # Aborting may discard already accepted READY; it is not G_EVENT retirement.
            for b in list(ready):
                if not s['trace_READY_full_o']&(1<<b): ready.pop(b)
        need(s['trace_live_tokens_o']==sum(1<<c['token'] for c in contexts.values()),'mother live token ownership')
        need(s['trace_block_active_o']==sum(1<<b for b in contexts),'mother target reservation ownership')
        need(s['trace_terminal_full_o']==sum(1<<b for b,c in contexts.items() if c['terminal'] is not None),'mother terminal slot accounting')
        need(s['trace_READY_full_o']==sum(1<<b for b in ready),'mother READY slot accounting')
        need(bool(s['trace_ireg_valid_o'])==(ireg is not None),'mother IREG visibility/discard')
        if ireg is not None:
            need(s['trace_opcode_o']==ireg['word']>>120 and s['trace_pc_o']==ireg['pc'],'mother fetched PC/opcode')
        targets=s['local_enabled_i']!=0 and (not s['local_enabled_i']&1 or s['local_image_id0_i']!=0) and (not s['local_enabled_i']&2 or s['local_image_id1_i']!=0)
        snapshot_ok=job is None or s['local_enabled_i']==job['enabled'] and all(not job['enabled']&(1<<b) or
            s['local_image_id'+str(b)+'_i']==job['ids'][b] for b in (0,1))
        expected_valid=authorized and prepared and not s['poison_o'] and s['deploy_valid_i'] and s['deploy_generation_i']==generation and targets and snapshot_ok
        need(s['image_valid_o']==int(expected_valid),'mother cohort/image gate')
        if s['life_o'] in (6,8): need(not s['cfg_req_ready_o'],'mother runtime configuration interlock')
        if s['release_valid_i'] and s['release_ready_o']:
            need(s['life_o']==0 and s['release_epoch_i']>0,'mother release certificate'); authorized=True; release_epoch=s['release_epoch_i']
        if cf:
            need(cfg is None and job is None and authorized,'mother config ownership')
            op=s['cfg_req_op_i']; cfg=dict(op=op,address=s['cfg_req_address_i'],data=s['cfg_req_data_i'],cycle=t,mem_done=False,read_data=0)
            if op==0:
                need(s['cfg_req_generation_i']>generation and 144<=s['cfg_req_total_bytes_i']<=4736 and s['cfg_req_total_bytes_i']%16==0,'mother BEGIN metadata')
                generation=s['cfg_req_generation_i']; total=s['cfg_req_total_bytes_i']; written=readback=0; prepared=False
                ids=[s[n] for n in ['cfg_req_image_id_i','cfg_req_topology_id_i','cfg_req_abi_id_i','cfg_req_capacity_id_i']]
            elif op in (1,2):
                need(cfg['address']==(written if op==1 else readback) and cfg['address']+16<=total and
                     (op==1 or written==total),'mother load/readback prefix')
            elif op==3:
                need(written==readback==total and s['cfg_req_proof_i'],'mother proof before actual complete readback')
                header=image.parse_image(bytes(shadow[:total]),'mother')['header']
                need([header[k] for k in ['program_image_id','topology_id','native_abi_id','capacity_profile_id']]==ids,'mother header identities')
            elif op==4: need(header is not None,'mother PREPARE before verified'); prepared=True
            elif op==5: prepared=False
        if s['cfg_rsp_valid_o']:
            need(cfg is not None and t>cfg['cycle'] and s['cfg_rsp_status_o']==0 and s['cfg_rsp_generation_o']==generation,'mother cfg response association/status')
            need(cfg['op'] not in (1,2) or cfg['mem_done'],'mother cfg response before actual PM ACK')
            need(s['cfg_rsp_data_o']==cfg['read_data'],'mother actual cfg readback payload')
            if s['cfg_rsp_ready_i']:
                if cfg['op']==2: readback+=16
                cfg=None
        if sf:
            need(job is None and not contexts and cfg is None and expected_valid and s['start_credit_i'] and
                 s['start_args_i']==0 and s['start_generation_i']==generation and s['start_epoch_i']>=release_epoch and s['start_sequence_i']>last_start,
                 'mother START without image/result credit/namespace')
            starts+=1; last_start=s['start_sequence_i']; job=dict(job=s['start_job_i'],epoch=s['start_epoch_i'],sequence=last_start,
                enabled=s['local_enabled_i'],ids=[s['local_image_id0_i'],s['local_image_id1_i']])
            regs=[0]*8; ready={}; consumed=set(); bind_words={}; first_error=None; prefix_read=prefix_write=0; saturation=False
        if mf:
            need(pm is None and not mr,'mother single PM/no refill')
            a=s['pm_req_address_o']; owner=s['trace_pm_owner_o']; need(a%16==0 and a+16<=total,'mother PM address')
            if owner==0:
                need(cfg is not None and cfg['op'] in (1,2) and a==cfg['address'] and s['pm_req_write_o']==(cfg['op']==1),'mother cfg PM tuple')
            else:
                need(job is not None and not s['pm_req_write_o'],'mother runtime PM ownership')
                if owner==1: need(ireg is None and a==header['instruction_offset']+16*s['trace_pc_o'],'mother fetch address/IREG')
                else: need(a in [header['event_binding_offset']+16*i for i in range(header['event_binding_count'])],'mother binding address')
            pm=dict(owner=owner,address=a,write=s['pm_req_write_o'],data=s['pm_req_data_o'],pc=s['trace_pc_o'],cycle=t)
        if mr:
            need(pm is not None and t>pm['cycle'],'mother PM response without prior request')
            a=pm['address']; wanted=int.from_bytes(shadow[a:a+16],'little')
            if pm['owner']!=0 and a==case.get('fault_addr',-1): wanted^=case.get('fault_xor',0)
            if pm['write']: shadow[a:a+16]=pm['data'].to_bytes(16,'little'); wanted=0; written+=16
            need(s['pm_rsp_data_i']==wanted,'mother PM stored payload')
            if pm['owner']==0:
                need(not s['pm_rsp_error_i'] and cfg is not None,'mother config PM error/owner')
                cfg['mem_done']=True; cfg['read_data']=wanted if cfg['op']==2 else 0
            elif s['pm_rsp_error_i']:
                need(case.get('pm_error') and a==case['fault_addr'],'unplanned mother PM error'); ctrl_fault(10,pm['pc'])
            elif first_error is None and not poison_seen:
                if pm['owner']==1: ireg=dict(word=wanted,pc=pm['pc'],cycle=t)
                else: bind_words[a]=wanted
            pm=None
        incoming=None
        if rf:
            m=codec.unpack_record('event_message',s['return_packet_i'].to_bytes(64,'little')); b=m['source_block']
            need(job is not None and b in contexts and contexts[b]['accepted'] is not None and contexts[b]['accepted']<t,'return before accepted CALL')
            c=contexts[b]; need(all(m[k]==c['packet'][k] for k in ['job_id','epoch','task_sequence']),'mother return task identity')
            if m['kind']<2:
                need(m['kind']==0 and b not in ready and c['terminal'] is None and m['event_sequence']==1 and m['completion_token']==255,'mother READY slot/sequence')
                need(any(codec.unpack_record('event_binding',v.to_bytes(16,'little'))['source_block']==b and
                    codec.unpack_record('event_binding',v.to_bytes(16,'little'))['event_id']==m['event_id'] for v in bind_words.values()),'READY without loaded binding')
                ready[b]=dict(packet=m,cycle=t); ready_received+=1
            else:
                need(c['terminal'] is None and m['completion_token']==c['token'] and m['event_id']==255 and m['event_sequence']==0,
                     'mother terminal duplicate/token')
                need((m['kind']==2 and m['status']==0) or m['kind']==3 and m['status']!=0,'mother terminal status')
                c['terminal']=dict(packet=m,cycle=t); prefix_read+=m['confirmed_read_bytes']; prefix_write+=m['confirmed_write_bytes']; saturation|=bool(m['flags']&1)
                if m['kind']==3:
                    incoming=m
                    if first_error is None:
                        first_error=dict(status=m['status'],pc=s['trace_pc_o'],source=b,child_pc=m['error_pc'],task=m['task_sequence'])
                    if pending is None or pending['kind']!=0: ireg=None
        if s['trace_retire_o']:
            need(ireg is not None and t>ireg['cycle'] and not s['poison_o'],'mother fabricated retirement')
            ins=codec.decode_instruction(ireg['word'],'mother'); op=ins['op']; retired.append(dict(pc=ireg['pc'],op=op,cycle=t))
            if op=='G_CALL': need(tf and pending is not None and pending['kind']==0,'G_CALL before whole message accept')
            elif op=='G_MOVI': need(first_error is None and incoming is None,'MOVI after abort'); regs[ins['a']]=ins['x']
            elif op=='G_EVENT':
                candidates=[codec.unpack_record('event_binding',v.to_bytes(16,'little')) for v in bind_words.values()]
                bind=next(v for v in candidates if v['event_id']==ins['b']); b=bind['source_block']
                need(first_error is None and b in ready and ready[b]['cycle']<t and ins['b'] not in consumed,'G_EVENT before prior accepted READY')
                regs[ins['a']]=ready.pop(b)['packet']['scalar']; consumed.add(ins['b'])
            elif op=='G_WAIT':
                selected=[b for b,c in contexts.items() if ins['x']&(1<<c['token'])]
                need(first_error is None and sum(1<<contexts[b]['token'] for b in selected)==ins['x'] and
                    all(contexts[b]['terminal'] is not None and contexts[b]['terminal']['cycle']<t and b not in ready for b in selected) and
                    all(codec.unpack_record('event_binding',v.to_bytes(16,'little'))['event_id'] in consumed
                        for v in bind_words.values() if codec.unpack_record('event_binding',v.to_bytes(16,'little'))['source_block'] in selected),
                    'G_WAIT before child/READY drain')
                for b in selected: contexts.pop(b)
            elif op=='G_END': need(ef and not contexts and not ready and first_error is None,'G_END before global result/child drain')
            else: need(False,'mother unsupported retirement')
            ireg=None
        if tf:
            need(pending is not None,'mother accepted unobserved packet'); b=pending['block']
            if pending['kind']==0: contexts[b]['accepted']=t; calls+=1
            else: contexts[b]['cancel']=True; cancels+=1
            pending=None
        # Decode failures are predicted from the actual fetched instruction and
        # public bounded-capacity state, not from a DUT error output.
        if ireg is not None and s['seq_o']==3 and first_error is None and incoming is None and not s['poison_o']:
            word=ireg['word']; pc=ireg['pc']; opbyte=word>>120; status=0
            if opbyte not in [0x10,0x11,0x12,0x13,0x1f]: status=1
            else:
                try: ins=codec.decode_instruction(word,'mother')
                except ValueError: status=7 if opbyte==0x11 else 2; ins=None
                if ins:
                    op=ins['op']
                    if op=='G_CALL':
                        if ins['a']>=2 or ins['b']>=8 or ins['c']!=0: status=2
                        elif not job['enabled']&(1<<ins['a']): status=4
                        elif ins['a'] in contexts and pending is None or ins['b'] in [c['token'] for c in contexts.values()] and pending is None: status=7
                    elif op=='G_WAIT':
                        mask=sum(1<<c['token'] for c in contexts.values())
                        if not ins['x'] or ins['x']&~mask: status=7
                        elif all(c['terminal'] is not None and c['terminal']['cycle']<t for c in contexts.values() if ins['x']&(1<<c['token'])):
                            selected={b for b,c in contexts.items() if ins['x']&(1<<c['token'])}
                            if any(b in ready for b in selected) or any(codec.unpack_record('event_binding',v.to_bytes(16,'little'))['event_id'] not in consumed
                                for v in bind_words.values() if codec.unpack_record('event_binding',v.to_bytes(16,'little'))['source_block'] in selected): status=7
                    elif op=='G_EVENT':
                        ids0=[codec.unpack_record('event_binding',v.to_bytes(16,'little'))['event_id'] for v in bind_words.values()]
                        if ins['b'] not in ids0: status=5
                        elif ins['b'] in consumed: status=7
                    elif op=='G_END' and (contexts or ready): status=7
            if status: ctrl_fault(status,pc)
        if first_error is None and job is not None and s['seq_o']==1 and s['trace_pc_o']>=header['instruction_count']: ctrl_fault(6,s['trace_pc_o'])
        if s['result_valid_o']:
            need(job is not None and not contexts and pending is None and pm is None,'global result before reserved obligations closed')
            e=first_error or dict(status=0,pc=0xffffffff,source=255,child_pc=0xffffffff,task=0)
            need((s['result_job_o'],s['result_epoch_o'],s['result_sequence_o'])==(job['job'],job['epoch'],job['sequence']),'global result namespace')
            need((s['result_status_o'],s['result_error_pc_o'],s['result_source_o'],s['result_child_error_pc_o'],s['result_failed_task_sequence_o'])==
                (e['status'],e['pc'],e['source'],e['child_pc'],e['task']),'global error cause/PC provenance')
            need((s['result_confirmed_read_bytes_o'],s['result_confirmed_write_bytes_o'],s['result_counter_overflow_o'],s['result_saturated_o'])==
                (min(prefix_read,0xffffffff),min(prefix_write,0xffffffff),int(prefix_read>0xffffffff or prefix_write>0xffffffff),int(saturation)),
                'global confirmed prefix/overflow')
            if ef:
                expected=0 if case.get('recover') and results>0 else case.get('expected',0)
                need(e['status']==expected,'mother scenario outcome'); results+=1; job=None; ireg=None; first_error=None
        if s['poison_o']:
            need(case.get('poison') and job is not None and not s['start_ready_o'] and not s['cfg_req_ready_o'] and
                 not s['image_valid_o'] and not s['result_valid_o'],'mother poison released result/admission')
            if not poison_seen:
                need(case.get('bad_return') or case.get('mode')==5 or stall_age>=1023,'mother poison before cause/deadline')
            poison_seen=True
        need(not poison_seen or s['poison_o'],'mother poison not sticky')
        if s['life_o']==6 and not s['result_valid_o']:
            stall_age=0 if mf or mr or tf or rf or s['trace_retire_o'] else stall_age+1
    need(starts==case.get('runs',1) and calls==case['calls'] and cancels==case.get('cancels',0),'mother start/CALL/CANCEL counts')
    need(results==(0 if case.get('poison') else case.get('runs',1)) and poison_seen==bool(case.get('poison')),'mother results/poison counts')
    if not poison_seen: need(job is None and not contexts and pending is None and pm is None and cfg is None and ireg is None,'unclosed mother boundary')
    return dict(cycles=len(rows),starts=starts,CALLs=calls,CANCELs=cancels,READY_received=ready_received,results=results,
        poisoned=poison_seen,retired=retired,actual_mother_RTL=True,actual_local_RTL=False,control_tokens=8,targets=2)


def mutations(traces,cases):
    out=[]
    for name,source,pin,predicate,value in [
        ('corrupt_CALL_arg','receiver_first','task_packet_o',lambda s:s['task_valid_o'],0),
        ('fake_GWAIT_retire','single_stalled','trace_retire_o',lambda s:s['trace_ireg_valid_o'] and s['trace_opcode_o']==0x11 and not s['trace_retire_o'],1),
        ('erase_terminal_receive','single_stalled','return_valid_i',lambda s:s['return_valid_i'] and s['return_ready_o'],0),
        ('poison_start_credit','missing_child','start_ready_o',lambda s:s['poison_o'],1)]:
        edited=copy.deepcopy(traces[source]); row=next(r for r in edited if predicate(r['signals'])); row['signals'][pin]=value
        try: check(edited,cases[source])
        except (ValueError,KeyError,StopIteration): out.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted mother mutation '+name)
    return out
