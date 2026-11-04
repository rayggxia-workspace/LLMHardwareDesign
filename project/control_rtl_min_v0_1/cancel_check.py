"""Check observed cancellation traces; never produce or repair DUT signals."""
import copy
import run as common

base=common.check_cycles
codec=common.codec


class CancelChecker(base.Checker):
    def cycle(self,t,s):
        task_fire=s['task_valid_i'] and s['task_ready_o']
        if task_fire and codec.unpack_record('task_message',s['task_packet_i'].to_bytes(64,'little'))['kind']==0:
            self.cancelled=False
        terminal=None
        if s['event_valid_o'] and s['event_ready_i']:
            terminal=codec.unpack_record('event_message',s['event_packet_o'].to_bytes(64,'little'))
        aborted_native=bool(self.cancelled and terminal and terminal['kind']==3 and terminal['status']==9)
        if aborted_native:
            base.need(not s['trace_retire_o'],'cancel error must not fabricate END retirement')
        super().cycle(t,s)
        if aborted_native:
            # v0.1 already discards an unretired IREG on accepted CANCELLED(11).
            # The same architectural abort point applies to its native-error(9)
            # precedence case. No prior-cycle signals or obligations are changed.
            self.ireg=None


def check(trace,poison=False,expected_cancels=1):
    monitor=CancelChecker(); monitor.block=trace.get('block',0)
    result=monitor.check(trace,complete=not poison)
    active=None; cancelled=False; frozen=False; cancel_pc=None; issued_pc=None
    error=0; allowed_pm=None; allowed_svc=None; previous=base.sample({})
    calls=cancels=terminals=cleanups=0; poison_seen=False
    def tuple_for(s,names): return tuple(s[n] for n in names)
    pm_fields=['pm_req_write_o','pm_req_address_o','pm_req_data_o','trace_pm_owner_o']
    svc_fields=['svc_req_kind_o','svc_req_resource_o','svc_req_token_o','svc_req_sequence_o',
        'svc_req_job_o','svc_req_epoch_o','svc_req_task_sequence_o','svc_req_descriptor_o',
        'svc_req_object_base_o','svc_req_object_length_o','svc_req_object_version_o']
    for row in trace['cycles']:
        s=base.sample(row['signals'])
        if not s['rst_ni']:
            active=None; cancelled=False; frozen=False; allowed_pm=None; allowed_svc=None
            previous=s; continue
        tf=s['task_valid_i'] and s['task_ready_o']
        sf=s['svc_req_valid_o'] and s['svc_req_ready_i']
        mf=s['pm_req_valid_o'] and s['pm_req_ready_i']
        ef=s['event_valid_o'] and s['event_ready_i']
        if tf:
            packet=codec.unpack_record('task_message',s['task_packet_i'].to_bytes(64,'little'))
            if packet['kind']==0:
                base.need(active is None,'overlapping CALL')
                active=packet; calls+=1; cancelled=False; frozen=False; error=0; issued_pc=None
            else:
                cancels+=1
                base.need(active is not None and all(packet[k]==active[k] for k in
                    ['target_block','job_id','epoch','task_sequence','task_descriptor','completion_token','program_image_id','topology_id']),
                    'cancel identity/profile mismatch')
                if not cancelled and not frozen:
                    if s['event_valid_o']:
                        frozen=True
                    else:
                        cancelled=True; cancel_pc=s['trace_pc_o']
                        allowed_pm=tuple_for(previous,pm_fields) if previous['pm_req_valid_o'] and not previous['pm_req_ready_i'] else None
                        allowed_svc=tuple_for(previous,svc_fields) if previous['svc_req_valid_o'] and not previous['svc_req_ready_i'] else None
        if cancelled:
            if s['pm_req_valid_o']:
                base.need(allowed_pm is not None and tuple_for(s,pm_fields)==allowed_pm,'new PM offer after cancel')
            if s['svc_req_valid_o']:
                base.need(allowed_svc is not None and tuple_for(s,svc_fields)==allowed_svc,'new service offer after cancel')
            if s['trace_retire_o']:
                base.need(sf and allowed_svc is not None,'fabricated instruction retirement during cancel')
            if mf: allowed_pm=None
            if sf: allowed_svc=None
        if sf: issued_pc=s['trace_pc_o']
        if s['svc_rsp_valid_i'] and s['svc_rsp_ready_o'] and s['svc_rsp_status_i']:
            error=s['svc_rsp_status_i']
        if s['trace_cancel_token_retire_o']: cleanups+=1
        if s['poison_o']:
            poison_seen=True
            base.need(s['life_o']==8 and not any(s[k] for k in
                ['image_valid_o','cfg_req_ready_o','task_ready_o','event_valid_o','trace_retire_o','trace_cancel_token_retire_o']),
                'poison isolation/ownership violation')
        if ef:
            base.need(active is not None,'terminal without CALL')
            status=(error or 11) if cancelled else error
            packet=codec.pack_record('event_message',dict(kind=3 if status else 2,source_block=trace.get('block',0),
                job_id=active['job_id'],epoch=active['epoch'],task_sequence=active['task_sequence'],
                completion_token=active['completion_token'],event_id=255,status=status,
                error_pc=(issued_pc if error else cancel_pc) if cancelled else (issued_pc if error else 0xffffffff)))
            base.need(s['event_packet_o']==int.from_bytes(packet,'little'),'full terminal packet/precedence mismatch')
            terminals+=1; active=None; cancelled=False; frozen=False
        previous=s
    base.need(cancels==expected_cancels,'accepted CANCEL count')
    base.need(poison_seen==poison,'unexpected/missing poison')
    base.need((terminals==0 and active is not None) if poison else (terminals==calls and active is None),'terminal count/ownership')
    result.update(actual_observed_cancellation=True,accepted_calls=calls,accepted_cancels=cancels,
        accepted_terminals=terminals,token_cleanups=cleanups,poisoned=poison_seen,drained=not poison)
    return result


def mutations(traces):
    cases=[]
    def rejected(name,trace,change):
        edited=copy.deepcopy(trace); change(edited)
        try: check(edited)
        except (ValueError,KeyError,IndexError):
            cases.append(dict(name=name,rejected=True)); return
        raise ValueError('observer accepted mutation '+name)
    held=traces['held_service']
    pm=traces['held_task_request']
    def alter_signal(t,condition,pin,value):
        row=next(r for r in t['cycles'] if condition(base.sample(r['signals'])))
        row['signals'][pin]=value
    rejected('withdraw_held_service',held,lambda t:alter_signal(t,
        lambda s:s['life_o']==7 and s['svc_req_valid_o'] and not s['svc_req_ready_i'],'svc_req_valid_o',0))
    rejected('withdraw_held_PM',pm,lambda t:alter_signal(t,
        lambda s:s['life_o']==7 and s['pm_req_valid_o'] and not s['pm_req_ready_i'],'pm_req_valid_o',0))
    rejected('fabricate_WAIT_retirement',traces['wait_service'],lambda t:alter_signal(t,
        lambda s:s['life_o']==7 and not s['trace_retire_o'],'trace_retire_o',1))
    rejected('premature_token_cleanup',traces['wait_service'],lambda t:alter_signal(t,
        lambda s:s['life_o']==7 and not s['svc_rsp_valid_i'] and not s['trace_cancel_token_retire_o'],'trace_cancel_token_retire_o',1))
    rejected('erase_accepted_CANCEL',traces['wait_service'],lambda t:alter_signal(t,
        lambda s:s['task_valid_i'] and s['task_ready_o'] and (s['task_packet_i']>>16)&255==1,'task_valid_i',0))
    rejected('hide_native_error',traces['native_error_same_edge'],lambda t:alter_signal(t,
        lambda s:s['event_valid_o'],'event_packet_o',0))
    return cases
