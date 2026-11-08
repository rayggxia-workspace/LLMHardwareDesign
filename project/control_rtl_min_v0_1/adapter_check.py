"""Observe immutable adapter pins and real native command/response edges."""
import copy,json,pathlib
import run as common
need=common.check_cycles.need
HERE=pathlib.Path(__file__).resolve().parent


def unit_trace(log):
    pins=json.loads((HERE/'adapter_pins.json').read_text(encoding='utf-8')); rows=[]
    for line in log.splitlines():
        if not line.startswith('A '): continue
        _,cycle,word=line.split(); word=int(word,16); s={}
        for p in reversed(pins): s[p['name']]=word&((1<<p['width'])-1); word>>=p['width']
        need(word==0,'trace width'); rows.append(dict(cycle=int(cycle),signals=s))
    return rows


def check_unit(rows,mode,canonical):
    active=None; pending=None; native=None; held={}; poisoned=False; cause=False
    accepts=commands=responses=returns=0
    channels=[('svc_req_valid_i','svc_req_ready_o',[k for k in rows[0]['signals'] if k.startswith('svc_req_') and k not in ['svc_req_valid_i','svc_req_ready_o']]),
        ('svc_rsp_valid_o','svc_rsp_ready_i',[k for k in rows[0]['signals'] if k.startswith('svc_rsp_') and k not in ['svc_rsp_valid_o','svc_rsp_ready_i']]),
        ('m_cmd_valid_o','m_cmd_ready_i',['m_cmd_op_o','m_cmd_index_o','m_cmd_data_o']),
        ('m_rsp_valid_i','m_rsp_ready_o',['m_rsp_data_i','m_rsp_error_i','m_rsp_saturated_i'])]
    for i,row in enumerate(rows):
        need(row['cycle']==i,'adapter trace continuity'); s=row['signals']
        if not s['rst_ni']:
            need(not any(s[k] for k in ['svc_req_ready_o','svc_rsp_valid_o','m_cmd_valid_o','m_rsp_ready_o']),'reset adapter admission')
            active=pending=native=None; held={}; poisoned=False; cause=False; continue
        for valid,ready,payload in channels:
            value=tuple(s[k] for k in payload)
            if valid in held: need(s[valid] and value==held[valid],'adapter held tuple '+valid)
            if s[valid] and not s[ready]: held[valid]=value
            else: held.pop(valid,None)
        if active is not None: need(not s['svc_req_ready_o'],'adapter overlapped ownership')
        if s['m_rsp_ready_o']: need(pending is not None and not poisoned,'native response readiness without command')
        if s['svc_req_ready_o']: need(s['provider_released_i'] and not s['poison_o'] and not s['m_rsp_valid_i'],'provider gate')
        if s['m_rsp_valid_i'] and pending is None: cause=True
        if not s['provider_released_i'] and active is not None: cause=True
        if s['poison_o']:
            need(cause and mode in (7,8,9),'unexplained adapter poison')
            poisoned=True
            need(not s['svc_req_ready_o'] and not s['svc_rsp_valid_o'] and not s['m_rsp_ready_o'],'poison retagged/completed native obligation')
        need(not poisoned or s['poison_o'],'adapter poison not sticky')
        if s['svc_req_valid_i'] and s['svc_req_ready_o']:
            need(active is None and not poisoned,'request overlap')
            active={k:s[k] for k in s if k.startswith('svc_req_')}
            active['cycle']=i; accepts+=1
            active['status']=4 if s['svc_req_kind_i'] or s['svc_req_resource_i'] else 5 if (
                s['svc_req_descriptor_i']!=canonical or any(s[k] for k in ['svc_req_object_base_i',
                'svc_req_object_length_i','svc_req_object_version_i'])) else 0
        if s['m_cmd_valid_o'] and s['m_cmd_ready_i']:
            need(active is not None and active['status']==0 and i>active['cycle'] and pending is None and not poisoned,
                 'native command before valid accepted service')
            need((s['m_cmd_op_o'],s['m_cmd_index_o'],s['m_cmd_data_o'])==(6,0,0),'native command encoding')
            pending=dict(cycle=i); commands+=1
        if s['m_rsp_valid_i'] and s['m_rsp_ready_o']:
            need(pending is not None and i>pending['cycle'] and native is None and not poisoned,'native response association')
            native=dict(cycle=i,status=9 if s['m_rsp_error_i'] or s['m_rsp_data_i'] else 0,saturated=s['m_rsp_saturated_i'])
            responses+=1
        if s['svc_rsp_valid_o']:
            need(active is not None and not poisoned and i>active['cycle'],'unassociated adapter response')
            if not active['status']: need(native is not None and native['cycle']<i,'service completion before real native response')
            status=active['status'] or native['status']
            need(s['svc_rsp_kind_o']==0 and s['svc_rsp_status_o']==status and
                 s['svc_rsp_read_bytes_o']==0 and s['svc_rsp_write_bytes_o']==0 and
                 s['svc_rsp_saturated_o']==(native['saturated'] if native else 0),'adapter status/counters')
            need(all(s['svc_rsp_'+k+'_o']==active['svc_req_'+k+'_i'] for k in
                 ['token','sequence','job','epoch','task_sequence']),'adapter immutable identity snapshot')
            if s['svc_rsp_ready_i']: returns+=1; active=pending=native=None
    need(accepts==(0 if mode==7 else 1),'adapter accepted count')
    need(returns==(0 if mode>=7 else 1),'adapter return count')
    need(commands==(1 if mode in (0,5,6) else 0) and responses==commands,'native count')
    need(poisoned==(mode>=7),'adapter poison count')
    return dict(cycles=len(rows),accepted=accepts,commands=commands,native_responses=responses,returns=returns,poisoned=poisoned)


def check_native(log,trace):
    samples={r['cycle']:common.check_cycles.sample(r['signals']) for r in trace['cycles']}
    active=None; cmd=None; done=None; count=0
    for line in log.splitlines():
        if not line.startswith('N '): continue
        v=line.split(); t=int(v[1]); cv,cr,op,index=map(int,v[2:6]); data=int(v[6],16)
        rv,rr,error=map(int,v[7:10]); result=int(v[10],16); poison=int(v[11])
        s=samples[t]; need(not poison,'real-native adapter poison')
        if s['svc_req_valid_o'] and s['svc_req_ready_i']:
            need(active is None,'native bridge service overlap'); active=t; cmd=done=None
        if cv and cr:
            need(active is not None and t>active and cmd is None and (op,index,data)==(6,0,0),'real-native command mapping/order')
            cmd=t
        if rv and rr:
            need(cmd is not None and t>cmd and done is None and error==0 and result==0,'real-native response association')
            done=t
        if s['svc_rsp_valid_i'] and s['svc_rsp_ready_o']:
            need(done is not None and t>done,'LC completed before real M response'); active=cmd=done=None; count+=1
    need(active is None,'unclosed real-native bridge service')
    return dict(real_native_services=count,macro='block_v2_m',native_op=6,only_clear_validity=True)


def mutations(rows,canonical):
    out=[]
    for name,pin,predicate,value in [
        ('wrong_native_opcode','m_cmd_op_o',lambda s:s['m_cmd_valid_o'],0),
        ('wrong_return_identity','svc_rsp_job_o',lambda s:s['svc_rsp_valid_o'],99),
        ('overlap_credit','svc_req_ready_o',lambda s:s['svc_rsp_valid_o'],1)]:
        edited=copy.deepcopy(rows); row=next(r for r in edited if predicate(r['signals'])); row['signals'][pin]=value
        try: check_unit(edited,0,canonical)
        except ValueError: out.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted adapter mutation '+name)
    return out
