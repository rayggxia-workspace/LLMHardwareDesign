"""Cross-controller observation; existing local/mother checkers see real signals."""
import copy
import run as common
import mc_check,transfer_check
need=common.check_cycles.need; codec=common.codec


def decode(log):
    mothers=mc_check.decode(log); locals=[]; events=[]
    for b in (0,1):
        stream=[]
        for line in log.splitlines():
            if line.startswith('L '+str(b)+' '): stream.append('T '+line.split(' ',2)[2])
            elif line.startswith('D '+str(b)+' '): stream.append('D '+line.split(' ',2)[2])
        text='\n'.join(stream); trace=common.decode_trace(text); trace['block']=b
        locals.append(trace); events.append(transfer_check.data_events(text))
    route=[]
    for line in log.splitlines():
        if line.startswith('N '):
            a=line.split(); route.append(dict(cycle=int(a[1]),kind=a[2],block=int(a[3]),job=int(a[4]),epoch=int(a[5]),task=int(a[6]),
                data=int(a[7],16) if a[2]=='STORE' else None,edge=int(a[7]) if a[2] in ['ARM','TX'] else None))
    return dict(mother=mothers,locals=locals,events=events,route=route)


def check(trace,case,images):
    mcase=dict(case,stall_limit=4096,cohort_revoked=bool(case.get('poison')))
    mother=mc_check.check(trace['mother'],mcase); local_results=[]
    for b in (0,1):
        expected=case['locals'][b]
        c=dict(expected,block=b,input_version_by_job={7:1,8:2})
        data=images['local'+str(b)]; h=codec.unpack_record('image_header',data[:128])
        if b==1 and case.get('mode') in (1,3): c.update(fault_addr=h['transfer_offset'],fault_xor=1,fault_jobs=[7])
        if b==0 and case.get('mode')==4: c.update(fault_addr=h['transfer_offset']+64,fault_xor=1)
        if case.get('mode')==3 and b==1: c['expected_status_by_job']={7:5,8:0}
        local_results.append(transfer_check.check(trace['locals'][b],c,data,trace['events'][b]))
    need(all(len(x['cycles'])==len(trace['mother']) for x in trace['locals']),'network sampling alignment')
    for i,mr in enumerate(trace['mother']):
        s=mr['signals']; ls=[common.check_cycles.sample(tr['cycles'][i]['signals']) for tr in trace['locals']]
        task_fire=s['task_valid_o'] and s['task_ready_i']; return_fire=s['return_valid_i'] and s['return_ready_o']
        accepted=[b for b in (0,1) if ls[b]['task_valid_i'] and ls[b]['task_ready_o']]
        returned=[b for b in (0,1) if ls[b]['event_valid_o'] and ls[b]['event_ready_i']]
        need(accepted==([s['task_target_o']] if task_fire else []),'Mother/LC task handshake not atomic')
        if task_fire:
            b=accepted[0]; need(ls[b]['task_packet_i']==s['task_packet_o'] and ls[b]['task_credit_i']==s['task_credit_o'],'Mother/LC whole task differs')
        need(len(returned)==int(bool(return_fire)),'LC/Mother return acceptance not atomic')
        if return_fire: need(ls[returned[0]]['event_packet_o']==s['return_packet_i'],'LC/Mother whole return differs')
    arms={}; tx=None; stored={}; ack_sent={}; unequal=0; route_events=0
    for e in trace['route']:
        t=e['cycle']; b=e['block']; key=(b,e['job'],e['epoch'],e['task'])
        if e['kind']=='ARM':
            need(b not in arms and e['edge']==11+b,'RX finite arm/route'); arms[b]=e
        elif e['kind']=='TX':
            need(tx is None and b==0 and 1 in arms and arms[1]['cycle']<t,'TX before receiver arm/duplicate finite TX')
            need((e['job'],e['epoch'],e['edge'])==(arms[1]['job'],arms[1]['epoch'],arms[1]['edge']),'TX/RX rendezvous namespace')
            tx=e; unequal+=int(e['task']!=arms[1]['task'])
        elif e['kind']=='STORE':
            need(b in arms and all(e[k]==arms[b][k] for k in ['job','epoch','task']) and arms[b]['cycle']<t and key not in stored,'router store without owned prior arm')
            pattern=int.from_bytes(bytes(range(16)),'little')^int.from_bytes((e['job']-6).to_bytes(4,'little')*4,'little')
            need(e['data']==pattern,'routed payload differs from this job input')
            need(b==0 or tx is not None and tx['cycle']<t,'consumer store before actual source TX')
            facts=trace['events'][b].get(t,[]); need(any(x['kind']==1 and x['data']==e['data'] for x in facts),'router store without actual finite SRAM write')
            if b==1: need(any(x['kind']==4 and x['data']==e['data'] for x in trace['events'][0].get(t,[])),'source sink-commit without destination store')
            stored[key]=t; route_events+=1
        elif e['kind']=='ACK_SEND':
            need(key in stored and stored[key]<t and b in arms,'ACK send before actual destination SRAM write')
            need(any(x['kind']==3 for x in trace['events'][b].get(t,[])),'RX completion without actual ACK-send accept')
            arms.pop(b); ack_sent[(e['job'],e['epoch'])]=t
        elif e['kind']=='ACK_RECV':
            need(tx is not None and all(e[k]==tx[k] for k in ['job','epoch','task']) and ack_sent.get((e['job'],e['epoch']),t)>=0 and
                 ack_sent.get((e['job'],e['epoch']),t)<t,'source ACK before receiver ACK/namespace')
            need(any(x['kind']==3 for x in trace['events'][0].get(t,[])),'TX complete without source ACK consumption'); tx=None
        else: need(False,'unknown route observation')
    if not case.get('poison'): need(not arms and tx is None,'network leftover link obligations')
    if case.get('mode')==3: need(unequal==1,'recovery did not exercise unequal endpoint task sequences')
    return dict(mother=mother,locals=local_results,route_stores=route_events,unequal_endpoint_task_sequence_pairs=unequal,
        actual_mother_RTL=True,actual_local_RTL=2,finite_SRAM_bytes_each=16384,native_S_RTL=False)


def mutations(traces,cases,images):
    result=[]
    for name in ['bad_routed_payload','broken_task_atomicity','premature_global_result','erase_TX_ACK']:
        tr=copy.deepcopy(traces['receiver_stalled'])
        if name=='bad_routed_payload': next(e for e in tr['route'] if e['kind']=='STORE')['data']=0
        elif name=='broken_task_atomicity':
            row=next(r for r in tr['locals'][0]['cycles'] if common.check_cycles.sample(r['signals'])['task_valid_i'] and common.check_cycles.sample(r['signals'])['task_ready_o'])
            row['signals']['task_packet_i']='0x0'
        elif name=='premature_global_result':
            row=next(r for r in tr['mother'] if r['signals']['trace_block_active_o']!=0); row['signals']['result_valid_o']=1
        else:
            t=next(t for t,es in tr['events'][0].items() if any(e['kind']==3 and e['service']==2 for e in es))
            tr['events'][0][t]=[e for e in tr['events'][0][t] if not(e['kind']==3 and e['service']==2)]
        try: check(tr,cases['receiver_stalled'],images['receiver'])
        except (ValueError,KeyError,StopIteration): result.append(dict(name=name,rejected=True)); continue
        raise ValueError('accepted network mutation '+name)
    return result
