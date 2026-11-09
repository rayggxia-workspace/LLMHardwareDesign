"""Independent profile provenance, trace work, and actual-request conservation."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
SCOPE='finite S32/W8/S96 local M control replay with actual S reservations; outer DDR/leases and unsupported paths retained; conditional old-system projection'
RTL_SHA='783089199218a48c3c6cfe78a67509dba1ee95ea23858f7c7e79737e7911510c'
GATES=('numeric','lifecycle','finite_resources','source_identity','real_S','control_replay','single_double_fairness')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def digest(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def read_calibration(path):
    path=Path(path);r=json.loads(path.read_bytes());p=r['profile']
    require(r.get('passed') is True and p.get('passed') is True,'unpassed finite calibration')
    require(re.fullmatch('[0-9a-f]{40}',r.get('source_commit','')) is not None,'calibration source commit absent')
    require(digest(r.get('manifest_sha256')) and digest(r.get('bank_sha256')),'calibration source binding absent')
    require(r['bank_sha256']=='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7','real SRAM macro source changed')
    require(r.get('physical_qualified') is False and r.get('full_P_DMA_integration') is False,'calibration qualification overstated')
    require(all(r.get('gates',{}).get(k) is True for k in GATES),'finite calibration gate missing')
    require(RTL_SHA in r['rtl_source_sha256'].values(),'different finite RTL source')
    require(r['rtl_source_sha256'].get('project/rtl/s_sram/block_feed_s16k_sram.sv')=='a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef','real SRAM controller source changed')
    require(r['vectors']['oracle']['passed'] is True and digest(r['vectors']['metadata_sha256']),'independent numerical oracle evidence absent')
    require(r['resource_ledger']['existing_P_S_bytes']==16384 and r['resource_ledger']['production_integration'] is False,'resource/integration ledger drift')
    control={name:sha(HERE/name) for name in ('finite_control.hpp','control_probe.cpp')}
    require(r['control_source_sha256']==control and p['control_source_sha256']==control,'control source not calibrated')
    shape=dict(A_bits=32,W_bits=8,logical_rows=1,N=8,K_packet=16,shift=16,old_tile_packets=16,old_tile_K=256,full_K=[2048,11008])
    require(p['schema_version']==1 and p['shape_contract']==shape,'unsupported finite shape contract')
    require(p['scope']=='actual finite M controller plus real four-bank S; replace whole qualified local service, not leaf-only II','profile scope drift')
    expected=dict(buffer_choices=[1,2],source_packet_bytes=256,S_bytes=16384,S_bank_count=4,S_bank_mode='1RW',
                  read_metadata=2,completion_reservations=8,nominal_read_bytes_per_packet=192,final_write_words=2,final_write_word_bytes=16)
    for k,v in expected.items():require(p[k]==v,'finite resource contract drift '+k)
    commands=r['commands'];runs=r['runs'];require(len(runs)==6,'finite six-run coverage absent')
    for command in commands:require(command['exit_code']==0 and digest(command['log_sha256']) and command['command'],'failed/unbound command')
    require({(q['BUFFERS'],q['mode'],q['seed']) for q in runs}=={(b,m,s) for b in (1,2) for m,s in ((1,143),(2,143),(2,144))},'buffer/reset seed coverage absent')
    read_delays=set();write_delays=set();row_ids=set();proofs=[];expected_labels={'qualified_ctx1_K2048','qualified_ctx1_K11008','qualified_ctx8_K2048','qualified_ctx8_K11008'}
    for run in runs:
        require(run['passed'] is True,'finite run failed')
        command=[x for x in commands if x['log']==run['log'] and x['command']==run['command'] and x['log_sha256']==run['log_sha256']]
        require(len(command)==1,'run not bound to executed command')
        c=run['control'];require(c.get('passed') is True and c.get('matched') is True and c.get('tampered_address_rejected') is True,'control comparison absent')
        require(c['compared_fields']>0 and c['cycles']>1 and c['initial_reset_rows_ignored']==1,'control field/reset proof absent')
        for k in ('raw_control_sha256','input_sha256','actual_sha256','probe_sha256'):require(digest(c[k]),'control identity absent '+k)
        require(c['probe_command'] in commands and c['probe_command']['stdin_sha256']==c['input_sha256'],'probe command/input binding absent')
        checks=run['checks'];require(checks['checks']>0 and checks['reset_cases']==20 and checks['cases']==len(run['case_measurements']),'numeric/lifecycle check coverage absent')
        qualified=[x for x in run['case_measurements'] if x['qualified']]
        require({x['label'] for x in qualified}==expected_labels,'fullK/context coverage absent')
        for q in qualified:
            require(not any(q[k] for k in ('read_delay','ack_delay','done_hold')),'nominal profile uses held response')
            require(digest(q['events_sha256']) and bool(q['events_file']),'events identity absent')
            d=q['derived'];count=q['valid'];require(q['invalid']==0 and count==q['commands'],'qualified command errors')
            for k,v in {'read_lines':3*count,'read_acks':3*count,'leaf_accepts':count,'commits':count,'completions':count}.items():
                require(q[k]==v and d[k]==v,'qualified actual work drift '+k)
            require(q['write_words']==q['write_acks']==d['write_words']==d['write_acks'] and q['write_words'] in (2,16),'qualified final write ACK drift')
            require(q['peak_buffers']<=run['BUFFERS'] and q['peak_reads']<=2 and q['peak_reservations']<=8,'actual finite resource overflow')
            require(q['accepted_to_done_cycles']==q['last_done']-q['first_accept']==d['accepted_to_done_cycles'],'measurement wall mismatch')
            require(q['accepted_to_next_ready_cycles']>=q['accepted_to_done_cycles'],'next acceptance boundary missing')
            read_delays.update(d['read_ack_cycle_deltas']);write_delays.update(d['write_ack_cycle_deltas'])
            matches=[x for x in p['rows'] if x['BUFFERS']==run['BUFFERS'] and x['mode']==run['mode'] and x['seed']==run['seed'] and x['measurement']==q]
            require(len(matches)==1,'measurement not uniquely represented in profile')
            entry=matches[0];require(entry['log']==run['log'] and entry['log_sha256']==run['log_sha256'] and entry['control_sha256']==c['raw_control_sha256'] and entry['events_sha256']==q['events_sha256'],'profile row evidence drift')
            row_ids.add((run['BUFFERS'],run['mode'],run['seed'],q['case']))
        proofs.append(dict(log=run['log'],log_sha256=run['log_sha256'],control_sha256=c['raw_control_sha256'],cycles=c['cycles'],compared_fields=c['compared_fields']))
    require(len(p['rows'])==len(row_ids)==24,'extra or missing finite profile rows')
    require(len(read_delays)==len(write_delays)==1 and min(read_delays)>0 and min(write_delays)>0,'nominal ACK latency requires backend FSM')
    require(p['ack_delays']['nominal_read_accept_to_consumed_ack_cycles']==sorted(read_delays) and p['ack_delays']['nominal_write_accept_to_consumed_ack_cycles']==sorted(write_delays),'ACK fee not actual FIFO-derived singleton')
    return dict(result_sha256=sha(path),source_commit=r['source_commit'],rtl_sha256=RTL_SHA,control_source_sha256=control,
                read_ack_cycles=next(iter(read_delays)),write_ack_cycles=next(iter(write_delays)),profile_scope=p['scope'],
                required_gates={k:True for k in GATES},measurement_sources=proofs,bank_sha256=r['bank_sha256'])

@lru_cache(None)
def inventory(trace,weight_bits):
    lines=Path(trace).read_text().splitlines();nt,no,tokens=map(int,lines[0].split());bits={}
    for line in lines[1:nt+1]:
        tid,e,b,initial=map(int,line.split());bits[tid]=b
    workers=[dict(old_tiles=0,final_outputs=0,old_adapter_cycles=0,old_M_cycles=0) for _ in range(2)]
    shapes={};operations=0
    for line in lines[nt+1:]:
        v=line.split();out,kind=int(v[0]),v[1];elements,rows,cols,k,batches,shift,layout,ni=map(int,v[2:10]);inputs=list(map(int,v[10:]))
        if kind!='Dot' or not (rows==1 and layout==0 and bits[inputs[0]]==32 and weight_bits==8 and shift==16 and k in (2048,11008) and cols%8==0):continue
        operations+=1;key=f'{rows}x{cols}x{k}b{batches}l{layout}';tiles=(cols//8)*(k//256)*batches
        shapes[key]=shapes.get(key,0)+tiles
        for worker in range(2):
            outputs=sum(1 for col in range(0,cols,8) if (col//16)%2==worker)*batches;t=outputs*(k//256)
            w=workers[worker];w['old_tiles']+=t;w['final_outputs']+=outputs;w['old_adapter_cycles']+=32*t;w['old_M_cycles']+=36*t+26*outputs
    require(len(lines)==1+nt+no,'trace line count mismatch')
    return dict(tokens=tokens,sha256=sha(trace),qualified_operations=operations,workers=workers,shape_old_tiles=shapes)

def check(row,baseline,trace,profile,buffers):
    meta=row['iteration3_study'];weight=8 if row['profile']=='queued_pipe_w8' else 16
    facts=inventory(str(Path(trace).resolve()),weight);active=bool(buffers and facts['qualified_operations'])
    require(meta['enabled'] is bool(buffers) and meta['buffers']==buffers and meta['scope']==SCOPE,'R3 enable/scope drift')
    require(meta['profile_available'] is True and meta['calibration_result_sha256']==profile['result_sha256'] and meta['calibration_source_commit']==profile['source_commit'] and meta['rtl_sha256']==RTL_SHA,'R3 calibration binding drift')
    require((meta['read_ack_cycles'],meta['write_ack_cycles'])==(profile['read_ack_cycles'],profile['write_ack_cycles']),'R3 ACK latency drift')
    for k,v in dict(source_slot_bytes=256,read_metadata=2,completion_reservations=8,old_tile_boundary_drain=True,same_edge_double_accept=False,
                    S_bytes=16384,A_RF_reuse=False,full_P_DMA_integration=False,physical_clock_qualified=False,full_LLM_RTL_numeric_proof=False).items():require(meta[k]==v,'R3 resource/scope drift '+k)
    require(len(meta['workers'])==2,'R3 worker count')
    require(set(row)==set(baseline)|{'iteration3_study'},'unexpected R3 fields')
    clean=deepcopy(row);clean.pop('iteration3_study')
    if not active:require(clean==baseline,'R3 disabled/fallback complete R2 RESULT mismatch')
    stable=('profile','tokens','read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors',
            'U_cache_peak_bytes','P_scratch_peak_bytes','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded',
            'M_tiles','KV_state_write_bytes','resident_A_saved_bytes','vector_work_ticks','compare_study','policy_study','iteration_study','iteration2_study')
    for k in stable:require(row[k]==baseline[k],'unchanged R2 work/state drift '+k)
    totals=dict(old_tiles=0,old_adapter_cycles=0,old_M_cycles=0,commands=0,core_active_cycles=0,read_requests=0)
    dual=row['hardware_study']['split_P_read_write_ports']
    for worker,(s,expected) in enumerate(zip(meta['workers'],facts['workers'])):
        expected=expected if active else dict.fromkeys(expected,0)
        require(s['worker']==worker,'worker identity')
        for k,v in expected.items():require(s[k]==v,'trace qualified work mismatch '+k)
        t=expected['old_tiles'];ends=expected['final_outputs']
        for k,v in dict(commands=t*16,leaf_accepts=t*16,commits=t*16,completions=t*16,read_requests=t*48,read_acks=t*48,write_requests=ends*2,write_acks=ends*2).items():require(s[k]==v,'finite traffic/work mismatch '+k)
        require(0<=s['peak_buffers']<=buffers and 0<=s['peak_reads']<=2 and 0<=s['peak_completions']<=8,'finite resource overflow')
        require(s['core_active_cycles']<=s['control_cycles'] and s['wall_subcycles']==1000*s['control_cycles'],'finite cycles ledger mismatch')
        require(s['alignment_subcycles']<1000*t if t else s['alignment_subcycles']==0,'clock edge alignment charge')
        if t:require(s['core_active_cycles']>=s['commands'] and s['control_cycles']>=s['read_requests']+s['write_requests'],'missing core/S/control service')
        else:require(all(v==0 for k,v in s.items() if k!='worker'),'fallback acquired finite resources')
        for k in totals:totals[k]+=s[k]
        old=baseline['hardware_study']['P_ports'][worker];new=row['hardware_study']['P_ports'][worker]
        service_delta=ends*1000;call_delta=47*t+ends
        read_service_delta=0 if dual else service_delta;read_call_delta=47*t if dual else call_delta
        require(new['read_or_unified_service_subcycles']==old['read_or_unified_service_subcycles']+read_service_delta and new['read_or_unified_reservations']==old['read_or_unified_reservations']+read_call_delta,'P input/narrow-output S accounting mismatch')
        require(new['write_service_subcycles']==old['write_service_subcycles']+(service_delta if dual else 0) and new['write_reservations']==old['write_reservations']+(ends if dual else 0),'P write port accounting mismatch')
        require(new['worker']==old['worker'] and new['DDR_channel']==old['DDR_channel'],'P topology changed')
        cal=row['detail']['S_calendars'][worker];prior=baseline['detail']['S_calendars'][worker]
        require(cal['service_subcycles']==prior['service_subcycles']+read_service_delta and cal['reservations']==prior['reservations']+read_call_delta,'detail S ledger differs from hardware ledger')
    require(row['M_commands']==baseline['M_commands']+15*totals['old_tiles'],'actual K16 commands omitted or duplicated')
    require(row['M_work_ticks']==baseline['M_work_ticks']-totals['old_M_cycles']+totals['core_active_cycles'],'M work definition/accounting mismatch')
    require(row['adapter_work_ticks']==baseline['adapter_work_ticks']-totals['old_adapter_cycles']+totals['read_requests'],'adapter work definition/accounting mismatch')
    for k,v in baseline['hardware_study'].items():
        if k not in ('P_ports','U_wait_subcycles'):require(row['hardware_study'][k]==v,'hardware/U work changed '+k)
    for group in (2,3):
        for k,v in baseline['detail']['S_calendars'][group].items():
            if 'wait' not in k:require(row['detail']['S_calendars'][group][k]==v,'unrelated S changed '+k)
    for a,b in zip(row['detail']['channels'],baseline['detail']['channels']):
        for k in ('channel','traffic','flows','beats','bus_work_subcycles'):require(a[k]==b[k],'DDR work changed '+k)
    for a,b in zip(row['detail']['matrix_shapes'],baseline['detail']['matrix_shapes']):
        delta=facts['shape_old_tiles'].get(b['key'],0)*15 if active else 0
        for k,v in b.items():
            if k=='wall_subcycles':continue
            require(a[k]==v+delta if k=='commands' else a[k]==v,'shape work changed '+k)
    for a,b in zip(row['detail']['P'],baseline['detail']['P']):
        for k,v in b.items():
            if not k.endswith('_subcycles'):require(a[k]==v,'outer P work changed '+k)
        require(a['elapsed_subcycles']==sum(a[k] for k in ('consumer_ready_wait_subcycles','input_ACK_wait_subcycles','service_subcycles','output_subcycles')),'P stages do not sum to elapsed')
    require(row['context_study']==baseline['context_study'],'outer context/A lease work changed')
    require(math.isclose(row['tokens_per_second']*row['seconds'],facts['tokens'],rel_tol=1e-9),'token metric mismatch')
    require(row['ticks']==(row['detail']['end_subcycles']+999)//1000 and
            math.isclose(row['seconds'],row['detail']['end_subcycles']/300000000000,rel_tol=1e-9),'clock/subcycle metric changed')
    return dict(passed=True,buffers=buffers,active=active,default_or_fallback_complete_R2_result_equal=not active,
                trace=facts,ledger=totals,DDR_and_U_work_unchanged=True,actual_S_narrow_write_difference_accounted=True,
                speedup_vs_same_layer_R2=baseline['seconds']/row['seconds'],counter_definitions_not_direct_speedup=True)

def reject_checks(row,*args):
    mutations=[('profile_identity',lambda x:x['iteration3_study'].__setitem__('calibration_result_sha256','0'*64)),
      ('missing_ack',lambda x:x['iteration3_study']['workers'][0].__setitem__('read_acks',x['iteration3_study']['workers'][0]['read_acks']+1)),
      ('free_output_S',lambda x:x['hardware_study']['P_ports'][0].__setitem__('write_service_subcycles',x['hardware_study']['P_ports'][0]['write_service_subcycles']+1000)),
      ('hidden_command',lambda x:x.__setitem__('M_commands',x['M_commands']+1)),
      ('changed_DDR',lambda x:x.__setitem__('read_bus_bytes',x['read_bus_bytes']+64)),
      ('changed_U',lambda x:x.__setitem__('vector_work_ticks',x['vector_work_ticks']+1)),
      ('free_A_RF',lambda x:x['iteration3_study'].__setitem__('A_RF_reuse',True)),
      ('false_physical',lambda x:x['iteration3_study'].__setitem__('physical_clock_qualified',True))]
    for name,mutate in mutations:
        bad=deepcopy(row);mutate(bad)
        try:check(bad,*args)
        except (ValueError,KeyError):pass
        else:raise ValueError('R3 corrupted result accepted '+name)
    return [name for name,_ in mutations]
