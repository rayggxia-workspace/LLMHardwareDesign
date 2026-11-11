"""R2 stateless-service provenance and paired R1-work conservation audit."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re

PROFILE_SCOPE='NExp supplemental compute wrapper service only; old vector_region unchanged'
PAYLOAD='signed low16 of each S32 container, U16 zeroextend to S32'
MODE='legacy_s32_low16_zeroextend_stateless_op12'
IMPLEMENTATION='native_stateless_relative_exp_op12'
SCOPE='replace R1 supplementary NExp service with measured stateless op12 wrapper service; original vector_region S/cache/DDR/E retained'
GATES=('compute_s32','full_U','numeric','lifecycle','default_compatibility','enabled_ordinary',
       'stateless_context_preservation','old_batch_compatibility')
R1_CALIBRATION_SHA='78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=4)
def legacy(repo):
    path=Path(repo)/'project/experiments/iterative_speed/round01/audit.py'
    spec=importlib.util.spec_from_file_location('round2_frozen_round1_audit',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def read_calibration(path):
    path=Path(path);receipt=json.loads(path.read_text(encoding='utf-8'))
    require(receipt.get('passed') is True,'R2 calibration did not pass')
    require(receipt.get('prior_calibration_result_sha256')==R1_CALIBRATION_SHA,'R2 compatibility prior is not actual run16')
    require(bool(re.fullmatch('[0-9a-f]{40}',receipt.get('source_commit',''))),'R2 source commit absent')
    rtl=receipt.get('rtl_source_sha256',{})
    require(bool(rtl) and all(re.fullmatch('[0-9a-f]{64}',v) for v in rtl.values()),'R2 RTL SHA map absent')
    gates=receipt.get('gates',{})
    require(all(gates.get(key) is True for key in GATES),'required R2 gate did not pass')
    require(receipt.get('physical_qualified') is False and receipt.get('native_N_instances')==1,'R2 resource/qualification scope changed')
    profile=receipt['profile']
    require(profile['schema_version']==1 and profile['scope']==PROFILE_SCOPE,'R2 service boundary changed')
    require(profile['payload_contract']==PAYLOAD and profile.get('implementation')==IMPLEMENTATION,'R2 implementation/semantic identity changed')
    require(profile.get('passed') is True and profile.get('fallback_input_bits')==[16],'R2 profile pass/fallback policy absent')
    rows=profile['rows']
    require(len(rows)==8 and sorted(r['count'] for r in rows)==list(range(1,9)),'R2 count1..8 profile incomplete')
    commands=receipt.get('commands',[]);runs=receipt.get('runs',[]);evidence={}
    def measured_source(row,label):
        require(row.get('passed') is True,'unpassed R2 measurement')
        log=row.get('log');digest=row.get('log_sha256');command=row.get('command')
        require(isinstance(log,str) and bool(log) and isinstance(digest,str) and bool(re.fullmatch('[0-9a-f]{64}',digest)),'R2 measurement log identity missing')
        require(isinstance(command,list) and bool(command) and all(isinstance(v,str) and v for v in command),'R2 measurement command absent')
        matches=[c for c in commands if c.get('log')==log and c.get('log_sha256')==digest and c.get('command')==command]
        require(len(matches)==1 and matches[0].get('exit_code')==0,'R2 measurement not bound to successful command')
        matches=[r for r in runs if r.get('label')==label and r.get('log')==log and r.get('log_sha256')==digest and
                 r.get('command')==command and r.get('mode')==row.get('mode') and r.get('seed')==row.get('seed')]
        require(len(matches)==1 and matches[0].get('passed') is True,'R2 measurement not bound to passed run')
        run=matches[0]
        if label in ('compute','full_U','stateless'):
            require(row.get('direct_mode')==1 and run.get('direct_mode')==1,'R2 measurement is not native direct mode')
        if label in ('compute','full_U'):
            observed=run.get('native_path',{})
            require(observed.get('direct_mode')==1 and observed.get('op12_commands',0)>0,'actual op12 command path not observed')
            if label=='compute':require(observed.get('other_commands')==0,'compute measurement still issued setup commands')
        if label=='compute':require(run.get('checks',{}).get('values',0)>=65536,'R2 numeric coverage absent')
        evidence[log]=dict(log_sha256=digest,command=command,label=label,mode=row['mode'],seed=row['seed'])
    # These are actual independent tests, not a Boolean supplied by the model.
    init_modes={(1,143),(2,143),(2,144)}
    stateless=[r for r in runs if r.get('label')=='stateless']
    require({(r.get('mode'),r.get('seed')) for r in stateless}==init_modes,'stateless proof initialization coverage missing')
    for row in stateless:
        measured_source(row,'stateless');proof=row.get('checks',{})
        require(proof.get('cases',0)>=10 and proof.get('checks',0)>0 and proof.get('reset_cases')==12,'stateless state/reset checks missing')
    for label in ('disabled_batch','disabled_compute','disabled_full_U'):
        compared=[r for r in runs if r.get('label')==label]
        require({(r.get('mode'),r.get('seed')) for r in compared}==init_modes,'old-batch comparison coverage missing')
        for row in compared:
            measured_source(row,label)
            require(row.get('exact_old_batch_match') is True,'old four-command path did not exactly reproduce R1')
    measured={n:[] for n in range(1,5)}
    for row in receipt['measurements']['compute_s32']:
        measured_source(row,'compute');n=row['count'];value=row['accepted_to_next_accept_cycles']
        require(type(n) is int and n in measured and row.get('mode32')==1,'unsupported R2 S32 frame')
        require(type(value) is int and type(row.get('accepted_to_done_cycles')) is int and 0<row['accepted_to_done_cycles']<value,'R2 accept interval invalid')
        measured[n].append(value)
    require(all(v and len(set(v))==1 for v in measured.values()),'R2 native frame calibration missing/nondeterministic')
    costs={n:v[0] for n,v in measured.items()};full_counts=set()
    for row in receipt['measurements']['full_U']:
        measured_source(row,'full_U')
        require(row['S_reads']==1 and row['S_writes']==1 and row['accepted_to_done_cycles']==
                row['input_stage_cycles']+row['compute_stage_cycles']+row['output_stage_cycles'],'R2 U stage work not conserved')
        if row['mode32']==1:full_counts.add(row['count'])
    require(full_counts=={1,2,3,4},'R2 full-U S32 coverage incomplete')
    ordered=[]
    for row in sorted(rows,key=lambda x:x['count']):
        n=row['count'];sub=[n] if n<=4 else [4,n-4]
        require(row['mode']==MODE and row['subcounts']==sub,'R2 profile must identify op12 and real S32 subframes')
        require(type(row['charge_cycles']) is int and row['charge_cycles']==sum(costs[c] for c in sub),'R2 charge not actual initiation interval sum')
        require(bool(row.get('derivation')),'R2 derivation missing');ordered.append(row)
    return dict(result_sha256=sha(path),source_commit=receipt['source_commit'],rtl_source_sha256=rtl,
        scope=PROFILE_SCOPE,payload_contract=PAYLOAD,implementation=IMPLEMENTATION,rows=ordered,
        compute_s32_intervals=costs,required_gates={key:gates[key] for key in GATES},measurement_sources=evidence)


def without_metadata(row):
    result=deepcopy(row);result.pop('iteration2_study',None);return result


def check(row,r1_baseline,run15_baseline,trace,r1_profile,r2_profile,enabled,repo):
    base=legacy(str(Path(repo).resolve()));facts=base.inventory(str(Path(trace).resolve()))
    active=bool(enabled and facts['qualified_operations']);meta=row['iteration2_study']
    require(meta['enabled'] is bool(enabled) and meta['scope']==SCOPE,'R2 enable/scope drift')
    require(meta['R1_enabled'] is True,'R2 evaluation requires R1 baseline enabled')
    require(meta['implementation']==IMPLEMENTATION and meta['profile_mode']==MODE and meta['payload_contract']==PAYLOAD,'R2 semantic/implementation identity drift')
    require(meta['new_profile_available'] is True and meta['native_profile_used'] is active,'R2 availability/format qualification drift')
    require(meta['old_calibration_result_sha256']==r1_profile['result_sha256'] and meta['new_calibration_result_sha256']==r2_profile['result_sha256'],'R2 calibration identity drift')
    require(meta['new_calibration_source_commit']==r2_profile['source_commit'],'R2 calibration source drift')
    require(meta['stateless_context_preservation_verified'] is True and meta['old_batch_compatibility_verified'] is True,'R2 stateless/default proof absent')
    require(meta['physical_clock_qualified'] is False and meta['full_LLM_RTL_numeric_proof'] is False,'R2 qualification overstated')
    require(meta['active_profile']==('R2_stateless' if active else 'R1_four_command'),'R2 active fee table mislabeled')
    stripped=without_metadata(row);selected=r2_profile if active else r1_profile
    # The frozen R1 audit checks all work and selected active calibration identity
    # against run15. A new table is never relabeled as the old table to pass it.
    checked=base.check(stripped,run15_baseline,trace,selected,True)
    r1_cost=r1_baseline['iteration_study']['charged_service_cycles']
    new_cost=sum(n*r2_profile['rows'][i-1]['charge_cycles'] for i,n in enumerate(facts['qualified_frames_by_count']) if i)+16*facts['fallback_values']
    charged=new_cost if active else r1_cost
    require((meta['R1_service_cycles'],meta['candidate_service_cycles'],meta['charged_service_cycles'])==(r1_cost,new_cost,charged),'R2 supplemental ledger drift')
    require(meta['delta_cycles']==charged-r1_cost,'R2 delta ledger drift')
    require(row['vector_work_ticks']-r1_baseline['vector_work_ticks']==charged-r1_cost,'R2 changed non-NExp arithmetic')
    exact=not active
    if exact:require(stripped==r1_baseline,'R2 default/fallback complete R1 RESULT regression failed')
    require(row['iteration_study']['calibration_result_sha256']==selected['result_sha256'],'actual service ledger uses wrong profile identity')
    return dict(passed=True,enabled=bool(enabled),native_profile_used=active,
        R1_service_cycles=r1_cost,candidate_service_cycles=new_cost,charged_service_cycles=charged,
        delta_cycles=charged-r1_cost,default_or_fallback_complete_R1_result_equal=exact,
        unchanged_M_S_cache_DDR_work=checked['unchanged_M_S_cache_DDR_work'],trace=facts,
        NExp_span_delta_cycles=row['spans_ticks']['NExp']-r1_baseline['spans_ticks']['NExp'],
        other_span_delta_cycles={k:row['spans_ticks'][k]-r1_baseline['spans_ticks'][k] for k in row['spans_ticks'] if k!='NExp'})


def reject_checks(row,*args):
    mutations=[
        ('new_profile_identity',lambda x:x['iteration2_study'].__setitem__('new_calibration_result_sha256','0'*64)),
        ('fake_active_profile',lambda x:x['iteration_study'].__setitem__('calibration_result_sha256','0'*64)),
        ('stateless_unverified',lambda x:x['iteration2_study'].__setitem__('stateless_context_preservation_verified',False)),
        ('missing_wrapper_cost',lambda x:x['iteration2_study'].__setitem__('charged_service_cycles',x['iteration2_study']['charged_service_cycles']-1)),
        ('hidden_M',lambda x:x.__setitem__('M_commands',x['M_commands']+1)),
        ('hidden_DDR',lambda x:x.__setitem__('write_bus_bytes',x['write_bus_bytes']+64)),
        ('hidden_S',lambda x:x['hardware_study'].__setitem__('U_service_subcycles',x['hardware_study']['U_service_subcycles']+1000)),
        ('false_physical',lambda x:x['iteration2_study'].__setitem__('physical_clock_qualified',True)),
    ]
    for name,mutate in mutations:
        bad=deepcopy(row);mutate(bad)
        try:check(bad,*args)
        except (ValueError,KeyError):pass
        else:raise ValueError('R2 negative accepted '+name)
    return [name for name,_ in mutations]
