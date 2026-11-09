"""R4 four-lane op12 provenance and R2-baseline work conservation."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path

MODE='legacy_s32_low16_zeroextend_stateless_op12_lanes4'
IMPLEMENTATION='native_stateless_relative_exp_op12_lanes4'
SCOPE='replace best-R2 supplementary NExp service with measured four-lane op12 wrapper service; original vector_region S/cache/DDR/E retained'
R2_CALIBRATION_SHA='fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78'
R2_AUDIT_SHA='3092bedd54e2c8a6ae08af008d78f07c3ea2ffd8906d968194a244620441a3f6'
NEW_GATES=('default_lanes2_compatibility','direct0_lanes4_compatibility','op12_lanes4_execution')
EXPECTED_RTL={
 'project/rtl/block_v2/block_v2_n.sv':'6efe29ed1121085d59bf072e2c3a062c9c18d67fa0f69a30da16f3b2b56f03ec',
 'project/rtl/pu_leaf_base/pu_u_group.sv':'f5e30680ab32cc0a96e25e60268549265fac92373966a449e447cf28df33b413',
 'project/rtl/pu_leaf_base/pu_nexp_shared.sv':'c0a4c727a128fdb06fb4f90f035a618ba400805d936c5290c0a8215f4a036ed5',
 'project/rtl/pu_leaf_base/nexp_batch_adapter.sv':'a975365f97ac8608760d2922e3843433624bd4db775441a8b48e0b2fb08679ca',
 'project/rtl/block_v2/block_v2_n_exp.svh':'a421489100aa883f645baeabfcefa1f4022010059d956f9770f44f2817c2a0ab',
}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@lru_cache(maxsize=4)
def frozen(repo):
    path=Path(repo)/'project/experiments/iterative_speed/round02/audit.py'
    require(sha(path)==R2_AUDIT_SHA,'frozen R2 audit source drift')
    spec=importlib.util.spec_from_file_location('round4_frozen_round2_audit',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def read_calibration(path,repo):
    # Reuse the proven provenance grammar, explicitly configured with the new
    # identity and actual run18 comparison. No receipt or measured fee is relabeled.
    source=Path(repo)/'project/experiments/iterative_speed/round02/audit.py'
    require(sha(source)==R2_AUDIT_SHA,'frozen provenance source drift')
    spec=importlib.util.spec_from_file_location('round4_profile_grammar',source)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    base.MODE=MODE;base.IMPLEMENTATION=IMPLEMENTATION;base.R1_CALIBRATION_SHA=R2_CALIBRATION_SHA
    base.GATES=tuple(base.GATES)+NEW_GATES
    profile=base.read_calibration(path);raw=json.loads(Path(path).read_bytes())
    for name,digest in EXPECTED_RTL.items():require(raw['rtl_source_sha256'].get(name)==digest,'R4 exact native/U/router/adapter/EXP source drift '+name)
    require(raw['profile'].get('direct_lanes')==4,'R4 profile is not four-lane native op12')
    commands=raw['commands'];runs=raw['runs'];init={(1,143),(2,143),(2,144)};lane_evidence=[]
    for label in ('compute','full_U','stateless'):
        selected=[r for r in runs if r['label']==label]
        require({(r['mode'],r['seed']) for r in selected}==init,'active R4 reset seed coverage missing '+label)
        for run in selected:
            require(run['direct_mode']==1 and run.get('direct_lanes')==4,'actual R4 run did not select lane4')
            lane=run.get('lane_path',{});native=run.get('native_path',{})
            require(lane.get('direct_mode')==1 and lane.get('direct_lanes')==4,'actual CALC lane path missing')
            require(lane.get('checked_commands',0)==lane.get('op12_completed',-1)>0,'CALC per-response checks absent')
            require(lane['checked_commands']<=lane.get('calc_steps',0)<=2*lane['checked_commands'],'four-lane CALC steps outside count1..8 contract')
            histogram=run.get('lane_counts',[])
            require(len(histogram)==8 and {h['count'] for h in histogram}==set(range(1,9)),'actual per-count CALC histogram absent')
            require(sum(h['commands'] for h in histogram)==lane['checked_commands'] and sum(h['calc_steps'] for h in histogram)==lane['calc_steps'],'actual CALC histogram does not conserve commands/steps')
            for h in histogram:
                require(h['calc_steps']==h['commands']*((h['count']+3)//4),'actual CALC histogram is not four-lane work')
                if label in ('compute','full_U'):require(h['commands']>0,'actual n1..8 tail execution missing')
            require(native.get('op12_lanes4_commands')==lane['checked_commands'],'native four-lane path not bound to checked CALC executions')
            if label=='compute':require(native.get('other_commands')==0,'R4 retained setup command sequence')
            require(any(c['log']==run['log'] and c['log_sha256']==run['log_sha256'] and c['command']==run['command'] and c['exit_code']==0 for c in commands),'lane proof not executed/bound')
            lane_evidence.append(dict(label=label,log=run['log'],log_sha256=run['log_sha256'],lane_path=lane,lane_counts=histogram))
    for name in ('compute_s32','full_U'):
        for measurement in raw['measurements'][name]:require(measurement.get('direct_lanes')==4,'measurement does not identify actual lane4')
    frames=raw['measurements']['compute_s32']
    require(len(frames)==12 and {(r['count'],r['mode'],r['seed']) for r in frames}==
            {(n,m,s) for n in range(1,5) for m,s in init},'R4 S32 frame/count/reset coverage incomplete')
    frames=raw['measurements']['full_U']
    expected={(fmt,n,m,s) for fmt,counts in ((0,range(1,9)),(1,range(1,5))) for n in counts for m,s in init}
    require(len(frames)==len(expected) and {(r['mode32'],r['count'],r['mode'],r['seed']) for r in frames}==expected,'R4 full-U S32/S16 count/reset coverage incomplete')
    default_evidence=[]
    for label in ('default_legacy','default_compute','default_full_U','default_stateless'):
        selected=[r for r in runs if r['label']==label]
        require({(r['mode'],r['seed']) for r in selected}==init,'default lane2 proof missing '+label)
        for run in selected:
            require(run['passed'] is True and run.get('direct_lanes')==2 and run.get('exact_default_lanes2_match') is True,'default lane2 does not reproduce R2')
            require(any(c['log']==run['log'] and c['log_sha256']==run['log_sha256'] and c['command']==run['command'] and c['exit_code']==0 for c in commands),'default lane2 proof not command-bound')
            default_evidence.append(dict(label=label,log=run['log'],log_sha256=run['log_sha256']))
    for label in ('disabled_batch','disabled_compute','disabled_full_U'):
        for run in runs:
            if run['label']==label:require(run.get('direct_mode')==0 and run.get('direct_lanes')==4 and run['exact_old_batch_match'] is True,'DIRECT0 changed under lane4')
    profile.update(direct_lanes=4,lane_execution_sources=lane_evidence,default_lanes2_sources=default_evidence)
    return profile

def check(row,baseline,run15,trace,r1_profile,r2_profile,profile,enabled,repo):
    original=frozen(str(Path(repo).resolve())).legacy(str(Path(repo).resolve()));facts=original.inventory(str(Path(trace).resolve()))
    active=bool(enabled and facts['qualified_operations']);meta=row['iteration4_study']
    require(meta['enabled'] is bool(enabled) and meta['scope']==SCOPE,'R4 enable/scope drift')
    require(meta['R1_enabled'] is True and meta['R2_enabled'] is True,'R4 must start from best R2')
    require(meta['implementation']==IMPLEMENTATION and meta['profile_mode']==MODE,'R4 implementation identity changed')
    require(meta['direct_lanes']==4 and meta['new_profile_available'] is True and meta['native_profile_used'] is active,'R4 lane/profile qualification drift')
    require(meta['old_calibration_result_sha256']==r2_profile['result_sha256'] and meta['new_calibration_result_sha256']==profile['result_sha256'] and meta['new_calibration_source_commit']==profile['source_commit'],'R4 source identity drift')
    require(meta['default_lanes2_compatibility_verified'] is True and meta['op12_lanes4_execution_verified'] is True,'R4 actual compatibility/execution proof absent')
    require(meta['physical_clock_qualified'] is False and meta['full_LLM_RTL_numeric_proof'] is False,'R4 qualification overstated')
    require(meta['active_profile']==('R4_lanes4' if active else 'R2_baseline'),'R4 active profile mislabeled')
    stripped=deepcopy(row);stripped.pop('iteration4_study')
    if active:
        require('iteration2_study' not in stripped and stripped.pop('iteration2_baseline_study')==baseline['iteration2_study'],'R2 baseline ledger changed or mislabeled current')
    else:
        require(stripped==baseline,'R4 off/fallback complete R2 result differs')
        require(stripped.pop('iteration2_study')==baseline['iteration2_study'],'R2 ledger changed')
    selected=profile if active else r2_profile if facts['qualified_operations'] else r1_profile
    checked=original.check(stripped,run15,trace,selected,True)
    old_cost=baseline['iteration_study']['charged_service_cycles']
    candidate=sum(n*profile['rows'][i-1]['charge_cycles'] for i,n in enumerate(facts['qualified_frames_by_count']) if i)+16*facts['fallback_values']
    charged=candidate if active else old_cost
    require((meta['R2_service_cycles'],meta['candidate_service_cycles'],meta['charged_service_cycles'],meta['delta_cycles'])==(old_cost,candidate,charged,charged-old_cost),'R4 actual supplemental fee ledger drift')
    require(row['vector_work_ticks']-baseline['vector_work_ticks']==charged-old_cost,'R4 changed other vector arithmetic')
    return dict(passed=True,enabled=bool(enabled),native_profile_used=active,default_or_fallback_complete_R2_result_equal=not active,
        R2_service_cycles=old_cost,candidate_service_cycles=candidate,charged_service_cycles=charged,delta_cycles=charged-old_cost,
        NExp_span_delta_cycles=row['spans_ticks']['NExp']-baseline['spans_ticks']['NExp'],
        other_span_delta_cycles={k:row['spans_ticks'][k]-baseline['spans_ticks'][k] for k in row['spans_ticks'] if k!='NExp'},
        unchanged_M_S_cache_DDR_work=checked['unchanged_M_S_cache_DDR_work'],R2_baseline_ledger_exact=True,trace=facts)

def reject_checks(row,*args):
    mutations=[('profile_identity',lambda x:x['iteration4_study'].__setitem__('new_calibration_result_sha256','0'*64)),
      ('lane2_disguised',lambda x:x['iteration4_study'].__setitem__('direct_lanes',2)),
      ('actual_lane_proof_absent',lambda x:x['iteration4_study'].__setitem__('op12_lanes4_execution_verified',False)),
      ('free_wrapper_fee',lambda x:x['iteration4_study'].__setitem__('charged_service_cycles',x['iteration4_study']['charged_service_cycles']-1)),
      ('hidden_M',lambda x:x.__setitem__('M_commands',x['M_commands']+1)),
      ('hidden_DDR',lambda x:x.__setitem__('write_bus_bytes',x['write_bus_bytes']+64)),
      ('hidden_U_S',lambda x:x['hardware_study'].__setitem__('U_service_subcycles',x['hardware_study']['U_service_subcycles']+1000)),
      ('false_physical',lambda x:x['iteration4_study'].__setitem__('physical_clock_qualified',True))]
    for name,mutate in mutations:
        bad=deepcopy(row);mutate(bad)
        try:check(bad,*args)
        except (ValueError,KeyError):pass
        else:raise ValueError('R4 accepted corrupted result '+name)
    return [name for name,_ in mutations]
