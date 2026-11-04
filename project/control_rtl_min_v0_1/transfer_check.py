"""Independent RAW16 control observer; samples and storage facts are immutable."""
import copy
import run as common
base=common.check_cycles; codec=common.codec; need=base.need


def data_events(log):
    out={}
    for line in log.splitlines():
        if not line.startswith('D '): continue
        _,t,kind,address,data,job,epoch,task,seq,service=line.split()
        out.setdefault(int(t),[]).append(dict(kind=int(kind),address=int(address,16),data=int(data,16),
            job=int(job),epoch=int(epoch),task=int(task),sequence=int(seq),service=int(service)))
    return out


def valid_transfer(raw,op,block):
    try: d=codec.unpack_record('transfer',raw)
    except ValueError: return False
    return (d['direction']==(op=='L_TX') and d['format']==4 and d['object_id']==0 and
        d['port_id']==d['peer_port']==d['peer_object']==0 and d['offset_reg']==d['count_reg']==d['invocation_reg']==d['fragment_reg']==255 and
        d['offset_bytes']==0 and d['count_bytes']==d['stride_bytes']==d['max_fragment_bytes']==16 and
        d['invocation']==d['object_version']==1 and d['fragment']==0 and
        ((op=='L_RX' and (block,d['peer_block'],d['edge_id']) in [(0,255,11),(1,0,12)]) or
         (op=='L_TX' and (block,d['peer_block'],d['edge_id'])==(0,1,12))))


def check(trace,case,data,events):
    block=case['block']; prefix=base.Checker(); prefix.block=block
    header=None; loaded=None; generation=0; active=None; pm=None; ireg=None; svc=None
    held={}; obj=None; valid=False; regs=[0]*8; records={}; calls=returns=reports=services=0
    reads=writes=0; service_seq=0; event_seq=0; cancelled=False; cancel_pc=None
    control_error=0; control_pc=None; native_error=0; native_pc=None; poisoned=False
    memory={}; peer_sink=None; ack_count=store_count=read_count=0; previous=None; last_sequence=0
    inv={v:k for k,v in base.LIFE.items()}; old_life='RESET_WAIT'
    for row in trace['cycles']:
        t=row['cycle']; s=base.sample(row['signals'])
        if not s['rst_ni']:
            prefix.cycle(t,s); active=pm=ireg=svc=None; held={}; obj=None; valid=False; regs=[0]*8
            header=None; poisoned=False; old_life='RESET_WAIT'; previous=s; continue
        life=inv[s['life_o']]
        if life!=old_life: need(life in base.C['transition_edges'][old_life],'transfer lifecycle transition')
        old_life=life
        for ch in base.C['channels']:
            name=ch['name']; value=tuple(s[k] for k in ch['payload'])
            if name in held: need(s[ch['valid']] and value==held[name],'RAW16 held tuple '+name)
            if s[ch['valid']] and not s[ch['ready']]: held[name]=value
            else: held.pop(name,None)
        tf=s['task_valid_i'] and s['task_ready_o']; mf=s['pm_req_valid_o'] and s['pm_req_ready_i']
        mr=s['pm_rsp_valid_i'] and s['pm_rsp_ready_o']; sf=s['svc_req_valid_o'] and s['svc_req_ready_i']
        sr=s['svc_rsp_valid_i'] and s['svc_rsp_ready_o']; ef=s['event_valid_o'] and s['event_ready_i']
        if header is None:
            prefix.cycle(t,s)
            if tf:
                header=prefix.header; loaded=bytes(prefix.shadow); generation=prefix.generation
            else: previous=s; continue
        need(s['image_valid_o']==int(not s['poison_o'] and s['deploy_valid_i'] and s['deploy_generation_i']==generation),'RAW16 deployment gate')
        if life in ('RUNNING','CANCELLING','POISONED'): need(not s['cfg_req_ready_o'],'RAW16 runtime reconfiguration')
        if s['svc_rsp_ready_o']:
            need(svc is not None and svc['done'] is None and
                 (s['svc_rsp_kind_i'],s['svc_rsp_token_i'],s['svc_rsp_sequence_i'])==(svc['kind'],svc['token'],svc['seq']) and
                 all(s[p]==active[k] for p,k in [('svc_rsp_job_i','job_id'),('svc_rsp_epoch_i','epoch'),('svc_rsp_task_sequence_i','task_sequence')]),
                 'RAW16 response readiness without matching owned command')
        if tf:
            m=codec.unpack_record('task_message',s['task_packet_i'].to_bytes(64,'little'))
            if m['kind']==0:
                need(active is None and obj is None and svc is None and s['task_credit_i'] and m['target_block']==block,
                     'RAW16 CALL ownership/credit')
                need(m['program_image_id']==header['program_image_id'] and m['topology_id']==header['topology_id'] and
                     m['epoch']>=prefix.cert_epoch and m['task_sequence']>last_sequence and m['task_descriptor']==0 and
                     m['completion_token']<8,'RAW16 CALL image/epoch/sequence')
                active=m; calls+=1; regs=[0]*8; records={}; service_seq=event_seq=0; reads=writes=0
                native_error=control_error=0; native_pc=control_pc=None; cancelled=False; cancel_pc=None
            else:
                need(active is not None and all(m[k]==active[k] for k in ['job_id','epoch','task_sequence','target_block',
                    'completion_token','program_image_id','topology_id']),'RAW16 CANCEL identity')
                need(not s['event_valid_o'] or (s['event_packet_o']>>16)&255>=2,'CANCEL admitted while locked READY')
                cancelled=True; cancel_pc=s['trace_pc_o']
        if mf:
            need(pm is None and active is not None and not s['pm_req_write_o'] and not poisoned,'RAW16 PM ownership')
            a=s['pm_req_address_o']; need(a%16==0 and a+16<=header['total_bytes'],'RAW16 PM range')
            pm=dict(address=a,owner=s['trace_pm_owner_o'],pc=s['trace_pc_o'],cycle=t)
        if mr:
            need(pm is not None and t>pm['cycle'] and not s['pm_rsp_error_i'],'RAW16 PM association')
            a=pm['address']; wanted=int.from_bytes(loaded[a:a+16],'little')
            if a==case.get('fault_addr',-1): wanted^=case.get('fault_xor',0)
            if case.get('zero_begin',-1)>=0 and case['zero_begin']<=a<case['zero_end']: wanted=0
            need(s['pm_rsp_data_i']==wanted,'unplanned RAW16 PM corruption')
            if pm['owner']==1: need(ireg is None,'RAW16 IREG overwritten'); ireg=dict(word=wanted,pc=pm['pc'],cycle=t)
            else: records[a]=wanted.to_bytes(16,'little')
            pm=None
        ins=codec.decode_instruction(ireg['word'],'local') if ireg else None
        if s['seq_o']==5 and ins and not cancelled:
            op=ins['op']
            if op in ('L_RX','L_TX'):
                td=codec.unpack_record('task',loaded[header['task_offset']:header['task_offset']+64])
                mask=td['input_object_mask'] if op=='L_RX' else td['output_object_mask']
                if not mask&1: control_error=4; control_pc=ireg['pc']
                elif not obj or svc or op=='L_TX' and not valid: control_error=7; control_pc=ireg['pc']
                else:
                    a=header['transfer_offset']+64*ins['c']
                    if all(a+i in records for i in range(0,64,16)) and not valid_transfer(b''.join(records[a+i] for i in range(0,64,16)),op,block):
                        control_error=5; control_pc=ireg['pc']
            elif op=='L_DROP' and (obj is None or svc is not None): control_error=7; control_pc=ireg['pc']
        if s['seq_o']==12:
            need(control_error or native_error or cancelled,'unexplained RAW16 fault drain')
            ireg=None; ins=None
        # Read response samples are pre-edge: a newly returned instruction only
        # becomes visible on the following sample.
        need(bool(s['trace_ireg_valid_o'])==(ireg is not None) or mr,'RAW16 IREG visibility')
        if sf:
            need(ins is not None and ins['op'] in ('L_RX','L_TX') and obj is not None and svc is None and not cancelled,
                 'RAW16 service without owned instruction/object')
            kind=1 if ins['op']=='L_RX' else 2; a=header['transfer_offset']+64*ins['c']
            need(all(a+i in records for i in range(0,64,16)),'service before complete transfer descriptor')
            raw=b''.join(records[a+i] for i in range(0,64,16))
            need(valid_transfer(raw,ins['op'],block),'invalid transfer issued')
            need(s['svc_req_kind_o']==kind and s['svc_req_resource_o']==5 and s['svc_req_token_o']==ins['b'] and
                s['svc_req_sequence_o']==service_seq and s['svc_req_descriptor_o']==int.from_bytes(raw,'little') and
                s['svc_req_object_base_o']==obj['base_bytes'] and s['svc_req_object_length_o']==16 and
                s['svc_req_object_version_o']==1,'RAW16 immutable request snapshot')
            need(all(s[p]==active[k] for p,k in [('svc_req_job_o','job_id'),('svc_req_epoch_o','epoch'),('svc_req_task_sequence_o','task_sequence')]),
                 'RAW16 service task identity')
            if kind==2: need(valid,'TX before prior successful RX WAIT')
            svc=dict(kind=kind,token=ins['b'],seq=service_seq,pc=ireg['pc'],cycle=t,done=None,write=None,read=None,sink=None,ack=None)
            service_seq+=1; services+=1
        for d in events.get(t,[]):
            need(svc is not None and t>svc['cycle'] and d['service']==svc['kind'] and d['sequence']==svc['seq'] and
                 (d['job'],d['epoch'],d['task'])==(active['job_id'],active['epoch'],active['task_sequence']) and
                 d['address']==obj['base_bytes'],'storage/ACK identity or ownership')
            pattern=int.from_bytes(bytes(range(16)),'little')^int.from_bytes(active['task_sequence'].to_bytes(4,'little')*4,'little')
            need(d['data']==pattern,'finite store/read payload differs from task input version')
            if d['kind']==1:
                need(svc['kind']==1 and svc['write'] is None,'duplicate/unowned SRAM write')
                memory[d['address']]=d['data']; svc['write']=t; store_count+=1
            elif d['kind']==2:
                need(svc['kind']==2 and svc['read'] is None and memory.get(d['address'])==d['data'],'TX read stale/unwritten data')
                svc['read']=t; read_count+=1
            elif d['kind']==4:
                need(svc['read'] is not None and svc['read']<t and svc['sink'] is None,'peer store before source read')
                peer_sink=d['data']; svc['sink']=t
            elif d['kind']==3:
                commit=svc['write'] if svc['kind']==1 else svc['sink']
                need(commit is not None and commit<t and svc['ack'] is None,'ACK before actual store/duplicate')
                if svc['kind']==2: need(peer_sink==d['data'],'ACK acknowledged wrong peer payload')
                svc['ack']=t; ack_count+=1
            else: need(False,'unknown finite storage event')
        if sr:
            need(svc is not None and svc['done'] is None and t>svc['cycle'],'RAW16 response association')
            need((s['svc_rsp_kind_i'],s['svc_rsp_token_i'],s['svc_rsp_sequence_i'])==(svc['kind'],svc['token'],svc['seq']) and
                 all(s[p]==active[k] for p,k in [('svc_rsp_job_i','job_id'),('svc_rsp_epoch_i','epoch'),('svc_rsp_task_sequence_i','task_sequence')]),
                 'RAW16 response identity')
            if case.get('mode')==3: need(svc['write'] is None and svc['ack'] is None and s['svc_rsp_status_i']==9,'write error fabricated data/ACK')
            else: need(svc['ack'] is not None and svc['ack']<t,'service completed before received/sent ACK')
            rb=16 if svc['kind']==2 and case.get('mode')!=3 else 0
            wb=16 if svc['kind']==1 and case.get('mode')!=3 else 0
            need((s['svc_rsp_read_bytes_i'],s['svc_rsp_write_bytes_i'],s['svc_rsp_saturated_i'])==(rb,wb,0),'RAW16 confirmed prefix')
            reads+=rb; writes+=wb; svc['done']=t
            if s['svc_rsp_status_i']: native_error=s['svc_rsp_status_i']; native_pc=svc['pc']
        if s['trace_cancel_token_retire_o']:
            need(cancelled and svc is not None and svc['done'] is not None and svc['done']<t,'RX cancel cleanup before actual response'); svc=None
        if s['trace_cancel_object_drop_o']:
            need(cancelled and obj is not None and svc is None and pm is None,'RX cancel object released before drain'); obj=None; valid=False
        if s['trace_retire_o']:
            need(ireg is not None and t>ireg['cycle'] and not poisoned,'RAW16 fabricated instruction retirement')
            ins=codec.decode_instruction(ireg['word'],'local'); op=ins['op']
            need(s['trace_pc_o']==ireg['pc'] and s['trace_opcode_o']==ireg['word']>>120,'RAW16 retiring word/PC')
            if op=='L_OPEN':
                a=header['object_offset']; need(obj is None and all(a+i in records for i in range(0,64,16)),'RAW16 OPEN before full record')
                obj=codec.unpack_record('object',b''.join(records[a+i] for i in range(0,64,16))); valid=False
            elif op=='L_MOVI': regs[ins['a']]=ins['x']
            elif op in ('L_RX','L_TX'): need(sf,'RX/TX retirement before adapter accept')
            elif op=='L_WAIT':
                need(svc is not None and svc['done'] is not None and svc['done']<t and ins['x']==1<<svc['token'],'WAIT before prior response')
                if svc['kind']==1 and not native_error: valid=True
                svc=None
            elif op=='L_REPORT':
                need(ef and (not native_error or sr or previous and previous['event_valid_o']),
                     'new READY after known provider failure')
            elif op=='L_DROP': need(obj is not None and svc is None,'DROP before ACK/token consumption'); obj=None; valid=False
            elif op=='L_END': need(ef and obj is None and svc is None,'END retained object/service')
            else: need(False,'unsupported RAW16 retirement')
            ireg=None
        if ef:
            m=codec.unpack_record('event_message',s['event_packet_o'].to_bytes(64,'little'))
            need(active is not None,'unowned RAW16 return')
            if m['kind']<2:
                # The report instruction is the actual fetched word at this PC.
                a=header['instruction_offset']+16*s['trace_pc_o']; w=int.from_bytes(loaded[a:a+16],'little')
                if a==case.get('fault_addr',-1): w^=case.get('fault_xor',0)
                ri=codec.decode_instruction(w,'local'); need(ri['op']=='L_REPORT','READY without REPORT')
                event_seq+=1
                expected=codec.pack_record('event_message',dict(kind=0,source_block=block,job_id=active['job_id'],epoch=active['epoch'],
                    task_sequence=active['task_sequence'],event_id=ri['a'],scalar=regs[ri['b']],event_sequence=event_seq))
                need(s['event_packet_o']==int.from_bytes(expected,'little'),'full READY / MOVI value readback')
                reports+=1
            else:
                need(pm is None and (svc is None or svc['done'] is not None and svc['done']<t),'terminal before finite peer drain')
                status=native_error or (11 if cancelled else control_error)
                pc=native_pc if native_error else cancel_pc if cancelled else control_pc if control_error else 0xffffffff
                need(status==case.get('expected',0),'terminal status not expected by independent scenario')
                if status: obj=None; valid=False; svc=None; ireg=None
                else: need(obj is None and svc is None,'success before object release')
                expected=codec.pack_record('event_message',dict(kind=3 if status else 2,source_block=block,job_id=active['job_id'],epoch=active['epoch'],
                    task_sequence=active['task_sequence'],completion_token=active['completion_token'],event_id=255,status=status,
                    confirmed_read_bytes=reads,confirmed_write_bytes=writes,error_pc=pc))
                need(s['event_packet_o']==int.from_bytes(expected,'little'),'full RAW16 terminal / confirmed prefix')
                returns+=1; last_sequence=active['task_sequence']; active=None; cancelled=False
        if s['poison_o']:
            poisoned=True
            need(case.get('poison') and active is not None and obj is not None and svc is not None and
                 not any(s[k] for k in ['image_valid_o','task_ready_o','cfg_req_ready_o','event_valid_o','trace_retire_o',
                    'trace_cancel_token_retire_o','trace_cancel_object_drop_o']),'RAW16 poison lost ownership/issued work')
        need(not poisoned or s['poison_o'],'RAW16 poison unstuck')
        previous=s
    need(calls==case.get('calls',1) and services==case['commands'] and reports==case['reports'],'RAW16 task/service/READY counts')
    need(returns==(0 if case.get('poison') else calls) and poisoned==bool(case.get('poison')),'RAW16 terminal/poison counts')
    if not poisoned: need(active is None and obj is None and svc is None and pm is None and ireg is None,'unclosed RAW16 obligation')
    return dict(cycles=len(trace['cycles']),calls=calls,services=services,READY_reports=reports,terminals=returns,
        local_stores=store_count,local_reads=read_count,ACK_accepts=ack_count,poisoned=poisoned,
        register_value_observed=reports>0,finite_SRAM_bytes=16384,native_S_tested=False)


def mutations(traces,cases,images,events):
    result=[]
    for name,source,pin,pred,value in [
        ('hide_READY_scalar','consumer','event_packet_o',lambda s:s['event_valid_o'] and (s['event_packet_o']>>16)&255==0,0),
        ('fabricate_TX_completion','producer','svc_rsp_ready_o',lambda s:s['svc_req_valid_o'] and s['svc_req_kind_o']==2,1),
        ('drop_before_ACK','producer','trace_retire_o',lambda s:s['seq_o']==9 and s['svc_rsp_valid_i']==0,1),
        ('poison_object_cleanup','missing_TX_ACK','trace_cancel_object_drop_o',lambda s:s['poison_o'],1)]:
        tr=copy.deepcopy(traces[source]); row=next(r for r in tr['cycles'] if pred(base.sample(r['signals']))); row['signals'][pin]=value
        try: check(tr,cases[source],images[cases[source]['image']],events[source])
        except ValueError: result.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted RAW16 mutation '+name)
    return result
