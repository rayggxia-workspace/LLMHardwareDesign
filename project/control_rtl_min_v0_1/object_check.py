"""Observe object reservations at real PM, retirement and cleanup boundaries."""
import copy
import run as common
import fault_check,cancel_check
base=common.check_cycles; codec=common.codec; need=base.need


def check(trace,case,data):
    h=codec.unpack_record('image_header',data[:128]); ob=h['object_offset']
    pm=None; fetched={}; ireg=None; obj=False; service=None; cancelled=False
    opened=dropped=cleaned=moves=0; poison_seen=False
    for row in trace['cycles']:
        s=base.sample(row['signals']); t=row['cycle']
        if not s['rst_ni']:
            pm=ireg=service=None; fetched={}; obj=False; cancelled=False; continue
        if s['task_valid_i'] and s['task_ready_o']:
            if (s['task_packet_i']>>16)&255==0:
                need(not obj and service is None,'new task inherited object/service'); fetched={}
            else: cancelled=True
        if s['pm_req_valid_o'] and s['pm_req_ready_i']:
            need(pm is None,'object PM overlap'); pm=(s['pm_req_address_o'],s['trace_pm_owner_o'],s['trace_pc_o'],t)
        if s['pm_rsp_valid_i'] and s['pm_rsp_ready_o']:
            need(pm is not None,'unowned object PM response')
            a,owner,pc,cycle=pm
            if not s['pm_rsp_error_i']:
                if owner==1: ireg=(s['pm_rsp_data_i'],pc)
                elif owner==2 and ob<=a<ob+64: fetched[a]=s['pm_rsp_data_i'].to_bytes(16,'little')
            pm=None
        if s['svc_req_valid_o'] and s['svc_req_ready_i']:
            need(service is None,'object service overlap'); service=dict(done=False)
        if s['svc_rsp_valid_i'] and s['svc_rsp_ready_o']:
            need(service is not None and not service['done'],'object service response association'); service['done']=True
        if s['trace_cancel_token_retire_o']:
            need(service is not None and service['done'],'cancel token before actual response'); service=None
        if s['trace_cancel_object_drop_o']:
            need(cancelled and obj and service is None and pm is None and s['life_o']==7,'cancel object released before drain')
            obj=False; fetched={}; cleaned+=1
        if s['trace_retire_o']:
            need(ireg is not None,'object retirement without fetched instruction')
            ins=codec.decode_instruction(ireg[0],'local')
            if ins['op']=='L_OPEN':
                need(not cancelled and not obj and ins['a']==0 and set(range(ob,ob+64,16))<=set(fetched),'OPEN before full descriptor/duplicate')
                record=codec.unpack_record('object',b''.join(fetched[a] for a in range(ob,ob+64,16)))
                need(record['object_id']==0 and record['kind']==0 and record['format']==4 and record['object_version']==1 and
                    record['capacity_bytes']==record['length_bytes']==16 and record['initial_valid_bytes']==0 and
                    record['native_abi_id']==65537 and record['base_reg']==record['length_reg']==255 and
                    record['base_bytes']%16==0 and record['base_bytes']+16<=16384,'bad object descriptor retired')
                obj=True; opened+=1
            elif ins['op']=='L_DROP':
                need(obj and service is None and ins['a']==0 and not cancelled,'DROP before object/service drain')
                obj=False; fetched={}; dropped+=1
            elif ins['op']=='L_MOVI': moves+=1
            elif ins['op']=='L_WAIT':
                need(service is not None and service['done'],'WAIT released object service early'); service=None
            elif ins['op']=='L_END': need(not obj and service is None,'END retained object/service')
            ireg=None
        if s['poison_o']:
            poison_seen=True
            need(not s['trace_cancel_object_drop_o'] and not s['event_valid_o'],'poison released object/task')
        if s['event_valid_o'] and s['event_ready_i']:
            status=(s['event_packet_o']>>144)&65535
            if status:
                need(service is None or service['done'],'fault object discarded before service response')
                if cancelled: need(not obj,'cancel terminal before object cleanup')
                obj=False; service=None; ireg=None; fetched={}
            else: need(not obj and service is None,'success retained object')
    if case.get('poison'): need(obj and service is not None and not service['done'],'poison lost outstanding ownership')
    else: need(not obj and service is None,'unclosed object')
    if case.get('cancel'):
        checked=cancel_check.check(trace,poison=bool(case.get('poison')))
    else:
        checked=fault_check.check(trace,case,extra_retire=lambda ins,s,t,loaded,header:ins['op'] in ['L_OPEN','L_DROP','L_MOVI'])
    checked.update(object_opens=opened,object_drops=dropped,cancel_object_cleanups=cleaned,movi_retirements=moves,
        register_value_observed=False,object_data_validated=False,logical_RAW16_reservation=True)
    return checked


def mutations(traces,cases,images):
    out=[]
    for name,source,pin,pred,value in [
        ('hide_cancel_object_cleanup','cancel_object','trace_cancel_object_drop_o',lambda s:s['trace_cancel_object_drop_o'],0),
        ('fake_OPEN_before_record','open_drop','trace_retire_o',lambda s:s['seq_o']==7,1),
        ('hide_object_fault','bad_object_ABI','event_packet_o',lambda s:s['event_valid_o'],0)]:
        edited=copy.deepcopy(traces[source]); row=next(r for r in edited['cycles'] if pred(base.sample(r['signals']))); row['signals'][pin]=value
        try: check(edited,cases[source],images[cases[source]['program']])
        except ValueError: out.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted object mutation '+name)
    return out
