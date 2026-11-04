"""Independent observer for the explicit runtime-fault profile and finite peers.

Input samples are immutable. The existing nominal checker validates every load
prefix; this observer checks runtime fault/abort semantics without relaxing it.
"""
import copy
import run as common

base=common.check_cycles
codec=common.codec
need=base.need


def check(trace,case):
    prefix=base.Checker(); prefix.block=trace.get('block',0)
    held={}; active=None; pm=None; service=None; ireg=None; header=None
    calls=returns=services=responses=0; poison_seen=False; poisoned=False
    fault=False; fault_observed=False; steps=0; last_sequence=0
    cfg_generation=0; cert_epoch=0; loaded=None; reset_after_poison=False
    prior=None; stall_age=0; terminal_cycle=None
    expected_returns=[]
    if not case.get('poison') and not case.get('reject'):
        expected_returns.append((case['expected'],case['error_pc']))
    if case.get('recovery'):
        expected_returns.append((0,0xffffffff))
    for row in trace['cycles']:
        t=row['cycle']; s=base.sample(row['signals'])
        if not s['rst_ni']:
            prefix.cycle(t,s)
            if poisoned: reset_after_poison=True
            active=pm=service=ireg=None; held={}; poisoned=False; fault=False
            header=None; last_sequence=0; stall_age=0; prior=s
            continue
        # Check every interface tuple across backpressure, including peers.
        for ch in base.C['channels']:
            value=tuple(s[k] for k in ch['payload']); name=ch['name']
            if name in held: need(s[ch['valid']] and value==held[name],'held tuple: '+name)
            if s[ch['valid']] and not s[ch['ready']]: held[name]=value
            else: held.pop(name,None)
        tf=s['task_valid_i'] and s['task_ready_o']
        mf=s['pm_req_valid_o'] and s['pm_req_ready_i']
        mr=s['pm_rsp_valid_i'] and s['pm_rsp_ready_o']
        sf=s['svc_req_valid_o'] and s['svc_req_ready_i']
        sr=s['svc_rsp_valid_i'] and s['svc_rsp_ready_o']
        ef=s['event_valid_o'] and s['event_ready_i']
        if header is None:
            prefix.cycle(t,s)
            if tf:
                header=prefix.header; loaded=bytes(prefix.shadow)
                cfg_generation=prefix.generation; cert_epoch=prefix.cert_epoch
            else:
                need(not s['poison_o'],'poison during nominal load')
                prior=s; continue
        need(s['image_valid_o']==int(not poisoned and not s['poison_o'] and s['deploy_valid_i'] and
             s['deploy_generation_i']==cfg_generation),'runtime deployment gate')
        if tf:
            m=codec.unpack_record('task_message',s['task_packet_i'].to_bytes(64,'little'))
            need(m['kind']==0 and active is None and s['life_o']==5 and s['task_credit_i'], 'CALL ownership')
            need(m['target_block']==trace.get('block',0) and m['epoch']>=cert_epoch and
                 m['task_sequence']>last_sequence and m['program_image_id']==header['program_image_id'] and
                 m['topology_id']==header['topology_id'],'CALL admission identity')
            active=m; calls+=1; fault=False; steps=0; issued_pc=None; terminal_cycle=None
        if s['life_o']==5: need(active is None or tf,'premature READY')
        if s['life_o'] in (6,7,8): need(not s['cfg_req_ready_o'],'runtime config interlock')
        injected=active is not None and active['task_sequence']==1
        if mf:
            need(pm is None and not mr and active is not None and not poisoned and not fault,'PM ownership after fault')
            a=s['pm_req_address_o']; owner=s['trace_pm_owner_o']
            need(not s['pm_req_write_o'] and a%16==0 and a+16<=header['total_bytes'] and owner in (1,2),'runtime PM range')
            if owner==1:
                need(ireg is None and a==header['instruction_offset']+16*s['trace_pc_o'],'fetch address/IREG ownership')
            pm=dict(address=a,owner=owner,pc=s['trace_pc_o'],cycle=t)
        if mr:
            need(pm is not None and t>pm['cycle'],'PM response before command')
            match=injected and pm['address']==case.get('fault_addr',-1)
            error=bool(match and case.get('pm_error'))
            need(bool(s['pm_rsp_error_i'])==error,'unplanned PM error')
            wanted=int.from_bytes(loaded[pm['address']:pm['address']+16],'little')
            if match: wanted^=case.get('fault_xor',0)
            need(s['pm_rsp_data_i']==wanted,'peer corruption does not match manifest')
            if error: fault=True; fault_observed=True
            elif pm['owner']==1:
                need(ireg is None,'overwrite IREG')
                ireg=dict(word=wanted,pc=pm['pc'],cycle=t)
            pm=None
        # A malformed instruction may be discarded at its architectural abort,
        # without claiming a retirement. The exact expected fault is external.
        if s['seq_o']==12 and not poisoned:
            need(active is not None,'fault drain without task')
            fault=True; fault_observed=True
            if ireg is not None:
                need(not s['trace_retire_o'],'faulting instruction retired')
                ireg=None
        need(bool(s['trace_ireg_valid_o'])==(ireg is not None) or mr and pm is None,
             'IREG visibility / unauthorized discard')
        if sf:
            need(not fault and not poisoned and service is None and ireg is not None,'service after fault/overlap')
            ins=codec.decode_instruction(ireg['word'],'local')
            need(ins['op']=='L_EXEC' and ins['a']==0 and ins['b']==s['svc_req_token_o'] and ins['c']==0,'service instruction')
            a=header['execution_offset']
            need(s['svc_req_kind_o']==0 and s['svc_req_resource_o']==0 and
                 s['svc_req_descriptor_o']==int.from_bytes(loaded[a:a+128],'little') and
                 not any(s[k] for k in ['svc_req_object_base_o','svc_req_object_length_o','svc_req_object_version_o']),
                 'service descriptor snapshot')
            need(all(s[p]==active[k] for p,k in [('svc_req_job_o','job_id'),('svc_req_epoch_o','epoch'),
                 ('svc_req_task_sequence_o','task_sequence')]),'service task snapshot')
            service=dict(token=ins['b'],seq=s['svc_req_sequence_o'],cycle=t,done=None)
            need(service['seq']==0,'service sequence restart')
            services+=1; issued_pc=ireg['pc']
        if sr:
            need(service is not None and service['done'] is None and t>service['cycle'],'service duplicate/early response')
            need(s['svc_rsp_kind_i']==0 and s['svc_rsp_token_i']==service['token'] and
                 s['svc_rsp_sequence_i']==service['seq'] and all(s[p]==active[k] for p,k in
                 [('svc_rsp_job_i','job_id'),('svc_rsp_epoch_i','epoch'),('svc_rsp_task_sequence_i','task_sequence')]),
                 'service response association')
            need(not any(s[k] for k in ['svc_rsp_read_bytes_i','svc_rsp_write_bytes_i','svc_rsp_saturated_i']),
                 'unexpected clear counters')
            service['done']=t; responses+=1
        if s['trace_retire_o']:
            need(ireg is not None and t>ireg['cycle'] and active is not None and not poisoned,'fabricated retirement')
            need(s['trace_pc_o']==ireg['pc'] and s['trace_opcode_o']==ireg['word']>>120,'retirement instruction')
            ins=codec.decode_instruction(ireg['word'],'local')
            if ins['op']=='L_EXEC': need(sf,'EXEC retirement without acceptance')
            elif ins['op']=='L_WAIT':
                need(service is not None and service['done'] is not None and service['done']<t and
                     ins['x']==1<<service['token'],'WAIT before matching prior response')
                service=None
            elif ins['op']=='L_END': need(ef and not service and not fault,'END retirement with obligations')
            else: need(False,'unsupported retirement')
            ireg=None; steps+=1
        if ef:
            need(active is not None and pm is None and (service is None or service['done'] is not None and
                 service['done']<t) and not poisoned,'terminal before external drain')
            need(returns<len(expected_returns),'extra terminal')
            status,pc=expected_returns[returns]
            wanted=codec.pack_record('event_message',dict(kind=3 if status else 2,source_block=trace.get('block',0),
                job_id=active['job_id'],epoch=active['epoch'],task_sequence=active['task_sequence'],
                completion_token=active['completion_token'],event_id=255,status=status,error_pc=pc))
            need(s['event_packet_o']==int.from_bytes(wanted,'little'),'full terminal/status/error PC')
            need(not status or fault_observed or service is not None,'unexplained fault terminal')
            returns+=1; last_sequence=active['task_sequence']; active=None; ireg=None; service=None
            terminal_cycle=t
        if s['poison_o']:
            need(case.get('poison') and active is not None and s['life_o']==8,'unplanned poison/lost task')
            need(not any(s[k] for k in ['task_ready_o','cfg_req_ready_o','image_valid_o','event_valid_o',
                 'trace_retire_o','trace_cancel_token_retire_o']),'poison emitted credit/work')
            need(pm is not None or service is not None and service['done'] is None or 'pm_req' in held or 'svc_req' in held,
                 'poison without retained obligation')
            if not poisoned: need(stall_age>=127,'poison before nonprogress deadline')
            poisoned=True; poison_seen=True
        # Independent clock count: progress means an actual accepted edge.
        obligation=pm is not None or service is not None and service['done'] is None or 'pm_req' in held or 'svc_req' in held
        stall_age=0 if mf or mr or sf or sr or not obligation else stall_age+1
        if prior and prior['poison_o'] and not s['poison_o']: need(False,'poison unstuck without reset')
        prior=s
    need(calls==(0 if case.get('reject') else 2 if case.get('recovery') else 1),'CALL count')
    need(returns==len(expected_returns) and services==case.get('commands',0),'terminal/service counts')
    need(poison_seen==bool(case.get('poison')),'poison coverage')
    if case.get('recovery')==2: need(reset_after_poison and active is None and not poisoned,'cohort peer reset/reload not observed')
    elif not case.get('poison'): need(active is None and pm is None and service is None and ireg is None,'unclosed task')
    return dict(actual_observed_fault=True,calls=calls,returns=returns,services=services,responses=responses,
                poisoned=poison_seen,peer_reset_reloaded=reset_after_poison,cycles=len(trace['cycles']))


def mutations(traces,cases):
    result=[]
    for name,trace_name,pin,predicate,value in [
        ('hide_error','bad_opcode','event_packet_o',lambda s:s['event_valid_o'],0),
        ('early_fault_retire','bad_opcode','trace_retire_o',lambda s:s['seq_o']==12,1),
        ('erase_service_accept','bad_WAIT','svc_req_valid_o',lambda s:s['svc_req_valid_o'] and s['svc_req_ready_i'],0),
        ('withdraw_terminal','bad_opcode','event_valid_o',lambda s:s['event_valid_o'],0),
        ('poison_credit','poison_M_response','task_ready_o',lambda s:s['poison_o'],1),
        ('corrupt_error_pc','bad_WAIT','event_packet_o',lambda s:s['event_valid_o'],0)]:
        edited=copy.deepcopy(traces[trace_name])
        row=next(r for i,r in enumerate(edited['cycles']) if predicate(base.sample(r['signals'])) and
            (name!='withdraw_terminal' or i>0 and
             base.sample(edited['cycles'][i-1]['signals'])['event_valid_o'] and
             not base.sample(edited['cycles'][i-1]['signals'])['event_ready_i']))
        row['signals'][pin]=value
        try: check(edited,cases[trace_name])
        except ValueError: result.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted mutation '+name)
    return result
