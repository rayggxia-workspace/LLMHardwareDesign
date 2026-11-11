"""Independent calibration, NExp histogram, and complete-work conservation audit."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

PROFILE_SCOPE='NExp supplemental compute wrapper service only; old vector_region unchanged'
PAYLOAD='signed low16 of each S32 container, U16 zeroextend to S32'
MODE='legacy_s32_low16_zeroextend'
FORMAT_POLICY='optimize S32-to-S32; S16-to-S32 remains legacy service'
RESULT_SCOPE='replace supplemental NExp service only; original vector_region S/cache/DDR/E service retained'
CALIBRATION_GATES=('compute_s32','full_U','numeric','lifecycle','default_compatibility','enabled_ordinary')


def require(ok,message):
    if not ok: raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_calibration(path):
    path=Path(path);receipt=json.loads(path.read_text(encoding='utf-8'))
    require(receipt.get('passed') is True,'NExp calibration did not pass')
    require(bool(re.fullmatch('[0-9a-f]{40}',receipt.get('source_commit',''))),'calibration source commit absent')
    rtl=receipt.get('rtl_source_sha256',{})
    require(bool(rtl) and all(re.fullmatch('[0-9a-f]{64}',v) for v in rtl.values()),'calibration RTL SHA map absent')
    gates=receipt.get('gates',{})
    require(all(gates.get(key) is True for key in CALIBRATION_GATES),'required integrated-U gate did not pass')
    require(receipt.get('physical_qualified') is False and receipt.get('native_N_instances')==1,'calibration resource/qualification scope changed')
    profile=receipt['profile']
    require(profile['schema_version']==1 and profile['scope']==PROFILE_SCOPE,'wrong calibrated-service scope')
    require(profile['payload_contract']==PAYLOAD,'wrong S32-container semantic boundary')
    require(profile.get('passed') is True and profile.get('fallback_input_bits')==[16],'profile pass/fallback policy absent')
    rows=profile['rows']
    require(len(rows)==8 and sorted(r['count'] for r in rows)==list(range(1,9)),'count1..8 calibration incomplete')
    commands=receipt.get('commands',[]);runs=receipt.get('runs',[])
    evidence={}
    def measured_source(row,label):
        require(row.get('passed') is True,'unpassed actual measurement')
        log=row.get('log');digest=row.get('log_sha256');command=row.get('command')
        require(isinstance(log,str) and bool(log) and isinstance(digest,str) and
                bool(re.fullmatch('[0-9a-f]{64}',digest)),'measurement log identity missing')
        require(isinstance(command,list) and bool(command) and all(isinstance(v,str) and v for v in command),'measurement command absent')
        matches=[c for c in commands if c.get('log')==log and c.get('log_sha256')==digest and c.get('command')==command]
        require(len(matches)==1 and matches[0].get('exit_code')==0,'measurement is not bound to a successful actual command')
        matches=[r for r in runs if r.get('label')==label and r.get('log')==log and r.get('log_sha256')==digest
                 and r.get('command')==command and r.get('mode')==row.get('mode') and r.get('seed')==row.get('seed')]
        require(len(matches)==1 and matches[0].get('passed') is True,'measurement is not bound to a passed actual run')
        if label=='compute':require(matches[0].get('checks',{}).get('values',0)>=65536,'numeric coverage gate missing from compute source')
        evidence[log]=dict(log_sha256=digest,command=command,label=label,mode=row['mode'],seed=row['seed'])
    measured={n:[] for n in range(1,5)}
    for r in receipt['measurements']['compute_s32']:
        measured_source(r,'compute')
        n=r['count'];require(type(n) is int and n in measured and r.get('mode32')==1,'unsupported native S32 frame count')
        value=r['accepted_to_next_accept_cycles']
        require(type(value) is int and value>0,'invalid measured initiation interval')
        require(type(r.get('accepted_to_done_cycles')) is int and 0<r['accepted_to_done_cycles']<value,'accept gap not measured')
        measured[n].append(value)
    require(all(v and len(set(v))==1 for v in measured.values()),'missing or nondeterministic S32 calibration points')
    full_counts=set()
    for r in receipt['measurements']['full_U']:
        measured_source(r,'full_U')
        require(r['S_reads']==1 and r['S_writes']==1 and r['accepted_to_done_cycles']==
                r['input_stage_cycles']+r['compute_stage_cycles']+r['output_stage_cycles'],'integrated-U stage work not conserved')
        if r['mode32']==1:full_counts.add(r['count'])
    require(full_counts=={1,2,3,4},'full integrated-U S32 count coverage incomplete')
    costs={n:v[0] for n,v in measured.items()}
    ordered=[]
    for row in sorted(rows,key=lambda x:x['count']):
        n=row['count'];sub=[n] if n<=4 else [4,n-4]
        require(row['mode']==MODE and row['subcounts']==sub,'S32 n8 cannot be a single S16 n8 frame')
        require(row['charge_cycles']==sum(costs[c] for c in sub),'model charge is not actual S32 subframe initiation sum')
        require(bool(row.get('derivation')),'charge derivation missing')
        ordered.append(row)
    return dict(result_sha256=sha(path),source_commit=receipt['source_commit'],rtl_source_sha256=rtl,
                scope=PROFILE_SCOPE,payload_contract=PAYLOAD,rows=ordered,compute_s32_intervals=costs,
                required_gates={key:gates[key] for key in CALIBRATION_GATES},measurement_sources=evidence)


@lru_cache(maxsize=32)
def inventory(trace_path):
    path=Path(trace_path);parts=path.read_text(encoding='utf-8').split();it=iter(parts)
    nt,no,tokens=(int(next(it)) for _ in range(3));tensors=[]
    for expected in range(nt):
        tid,elements,bits,initial=(int(next(it)) for _ in range(4))
        require(tid==expected,'tensor ID mismatch');tensors.append((elements,bits,initial))
    frames=[0]*9;qualified_frames=[0]*9;fallback_frames=[0]*9
    operations=values=qualified_operations=qualified_values=fallback_operations=fallback_values=0
    for _ in range(no):
        output=int(next(it));kind=next(it);elements=int(next(it))
        rows,cols,k,batches,shift,layout,ni=(int(next(it)) for _ in range(7))
        inputs=[int(next(it)) for _ in range(ni)]
        if kind=='NExp':
            require(ni==1 and tensors[inputs[0]][1] in (16,32) and tensors[output][1]==32,'NExp integer-container contract changed')
            require(elements<=tensors[inputs[0]][0] and elements==tensors[output][0],'NExp extent mismatch')
            operations+=1;values+=elements;full,tail=divmod(elements,8);frames[8]+=full
            if tail:frames[tail]+=1
            if tensors[inputs[0]][1]==32:
                qualified_operations+=1;qualified_values+=elements;selected=qualified_frames
            else:
                fallback_operations+=1;fallback_values+=elements;selected=fallback_frames
            selected[8]+=full
            if tail:selected[tail]+=1
    require(next(it,None) is None,'extra trace tokens')
    return dict(trace_sha256=sha(path),tokens=tokens,operations=operations,values=values,frames_by_count=frames,
                qualified_operations=qualified_operations,qualified_values=qualified_values,qualified_frames_by_count=qualified_frames,
                fallback_operations=fallback_operations,fallback_values=fallback_values,fallback_frames_by_count=fallback_frames)


def without_metadata(row):
    result=deepcopy(row);result.pop('iteration_study',None);return result


def check(row,baseline,trace,profile,enabled):
    # Cheap ledgers first so tampered large traces are rejected before scanning.
    meta=row['iteration_study'];costs=[0]+[r['charge_cycles'] for r in profile['rows']]
    require(meta['enabled'] is bool(enabled) and meta['profile_available'] is True,'enable/profile metadata mismatch')
    require(meta['scope']==RESULT_SCOPE and meta['input_format_policy']==FORMAT_POLICY,'result scope/format policy changed')
    require(meta['calibration_result_sha256']==profile['result_sha256'] and meta['calibration_source_commit']==profile['source_commit'],'calibration identity drift')
    require(meta['payload_contract']==PAYLOAD and meta['frame_cycles']==costs,'service profile drift')
    require(meta['physical_clock_qualified'] is False and meta['full_LLM_RTL_numeric_proof'] is False,'qualification overstated')
    stable=('profile','tokens','read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes',
            'dma_descriptors','U_cache_peak_bytes','P_scratch_peak_bytes','cache_hits','cache_misses','dirty_evictions',
            'dead_lines_discarded','M_commands','M_tiles','KV_state_write_bytes','resident_A_saved_bytes',
            'M_work_ticks','adapter_work_ticks','context_study','compare_study','policy_study')
    for key in stable: require(row[key]==baseline[key],'unchanged work/state drift '+key)
    require(row['hardware_study'].keys()==baseline['hardware_study'].keys(),'hardware contract keys changed')
    for key,value in baseline['hardware_study'].items():
        if key!='P_ports':require(row['hardware_study'][key]==value,'hardware/U local work changed '+key)
    require(len(row['hardware_study']['P_ports'])==len(baseline['hardware_study']['P_ports']),'P port count changed')
    for current,old in zip(row['hardware_study']['P_ports'],baseline['hardware_study']['P_ports']):
        for key,value in old.items():
            if 'wait' not in key:require(current[key]==value,'P S work/reservation changed '+key)
    require(len(row['detail']['channels'])==len(baseline['detail']['channels']),'DDR channel count changed')
    for current,old in zip(row['detail']['channels'],baseline['detail']['channels']):
        for key in ('channel','traffic','flows','beats','bus_work_subcycles'):
            require(current[key]==old[key],'DDR traffic/service drift '+key)
    require(row['detail']['S_calendars'].__len__()==baseline['detail']['S_calendars'].__len__(),'S count changed')
    for current,old in zip(row['detail']['S_calendars'],baseline['detail']['S_calendars']):
        for key,value in old.items():
            if 'wait' not in key:require(current[key]==value,'S service/reservation changed '+key)
    require(len(row['detail']['matrix_shapes'])==len(baseline['detail']['matrix_shapes']),'matrix shape count changed')
    for current,old in zip(row['detail']['matrix_shapes'],baseline['detail']['matrix_shapes']):
        for key,value in old.items():
            if key!='wall_subcycles':require(current[key]==value,'matrix shape work drift '+key)
    require(len(row['detail']['P'])==len(baseline['detail']['P']),'P worker count changed')
    for current,old in zip(row['detail']['P'],baseline['detail']['P']):
        for key,value in old.items():
            if not key.endswith('_subcycles'):require(current[key]==value,'P schedule work drift '+key)
    require(set(row)==set(baseline)|{'iteration_study'},'unexpected result fields')
    require(set(row['spans_ticks'])==set(baseline['spans_ticks']),'operation family changed')
    facts=inventory(str(Path(trace).resolve()))
    for key in ('operations','values','frames_by_count','qualified_operations','qualified_values','qualified_frames_by_count',
                'fallback_operations','fallback_values','fallback_frames_by_count'):
        require(meta[key]==facts[key],'NExp trace ledger mismatch '+key)
    require(meta['native_profile_used'] is bool(enabled and facts['qualified_operations']),'unqualified input used native profile')
    old_cost=16*facts['values'];new_cost=sum(a*b for a,b in zip(facts['qualified_frames_by_count'],costs))+16*facts['fallback_values'];charged=new_cost if enabled else old_cost
    require((meta['old_service_cycles'],meta['candidate_service_cycles'],meta['charged_service_cycles'])==(old_cost,new_cost,charged),'NExp selected-cost ledger drift')
    require(row['vector_work_ticks']-baseline['vector_work_ticks']==charged-old_cost,'non-NExp arithmetic changed')
    require(math.isclose(row['tokens_per_second']*row['seconds'],facts['tokens'],rel_tol=1e-9),'token metric inconsistency')
    exact_required=not enabled or facts['qualified_operations']==0
    if exact_required:require(without_metadata(row)==baseline,'default/fallback complete RESULT regression failed')
    return dict(passed=True,enabled=bool(enabled),trace=facts,old_service_cycles=old_cost,
        candidate_service_cycles=new_cost,charged_service_cycles=charged,
        supplemental_delta_cycles=charged-old_cost,
        NExp_span_delta_cycles=row['spans_ticks']['NExp']-baseline['spans_ticks']['NExp'],
        other_span_delta_cycles={k:row['spans_ticks'][k]-baseline['spans_ticks'][k] for k in row['spans_ticks'] if k!='NExp'},
        unchanged_M_S_cache_DDR_work=True,default_or_fallback_complete_result_equal=exact_required,
        scope='only supplementary NExp charge changes; original vector-region E/S/cache/DDR retained, waits may shift')


def reject_checks(row,baseline,trace,profile,enabled):
    mutations=[
        ('calibration_identity',lambda x:x['iteration_study'].__setitem__('calibration_result_sha256','0'*64)),
        ('missing_wrapper_cost',lambda x:x['iteration_study'].__setitem__('charged_service_cycles',x['iteration_study']['charged_service_cycles']-1)),
        ('hidden_M',lambda x:x.__setitem__('M_commands',x['M_commands']+1)),
        ('hidden_DDR',lambda x:x.__setitem__('write_bus_bytes',x['write_bus_bytes']+64)),
        ('hidden_U_S',lambda x:x['hardware_study'].__setitem__('U_service_subcycles',x['hardware_study']['U_service_subcycles']+1000)),
        ('hidden_vector_work',lambda x:x.__setitem__('vector_work_ticks',x['vector_work_ticks']+1)),
        ('tail_frame',lambda x:x['iteration_study']['frames_by_count'].__setitem__(1,x['iteration_study']['frames_by_count'][1]+1)),
        ('false_physical',lambda x:x['iteration_study'].__setitem__('physical_clock_qualified',True)),
    ]
    for name,mutate in mutations:
        bad=deepcopy(row);mutate(bad)
        try:check(bad,baseline,trace,profile,enabled)
        except (ValueError,KeyError):pass
        else:raise ValueError('negative accepted '+name)
    return [name for name,_ in mutations]
