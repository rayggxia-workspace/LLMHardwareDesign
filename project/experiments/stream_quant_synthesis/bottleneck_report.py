"""Verify immutable evaluation receipts and derive per-token comparisons."""
import argparse
import json
from pathlib import Path
from report import contents


def summarize(root):
    records={}
    members=0
    for tag in ('14','15','16'):
        files=contents(root/('run'+tag));members+=len(files)-1
        records[tag]=json.loads(files['results/bottleneck.json'])
    assert not records['14']['passed'] and 'misleading-indentation' in records['14']['error']
    assert records['15']['passed'] and records['16']['passed']
    r=records['16'];assert len(r['cases'])==16
    assert r['source_commit']=='014b34818cd1620340b7d2e3ab7f03c76149e698'
    assert r['native-g']['accepted']==264144 and r['native-g']['delivered']==264144
    assert r['rendezvous']['fifo_bytes']==16 and r['rendezvous']['reset_while_blocked']
    for c in r['rendezvous']['cases']:
        assert c['x_peak']<=2 and c['u_peak']<=2
        if not c['stalls']:assert c['packets']==32 and c['cycles']==37
    cases=[]
    for c in r['cases']:
        v=c['result'];nt=v['tokens'];clock=300e6
        ref=next(x['result'] for x in r['cases'] if x['workload']==c['workload'] and x['knobs']['SQ_BW_MB']==c['knobs']['SQ_BW_MB'] and not x['queued'] and x['release']==0)
        for key in r['work_invariants']:assert v[key]==ref[key]
        assert v['max_outstanding_beats']<=32 and v['P_scratch_peak_bytes']<=16384
        assert v['sq_study']['activation_bits']==0 and not v['sq_study']['quality_verified']
        assert v['sq_study']['native_full_model_tokens_per_second'] is None
        cases.append(dict(name=c['name'],tokens_s=v['tokens_per_second'],
            ms_per_token=v['seconds']*1000/nt,
            stage_ms_per_token={k:t/clock*1000/nt for k,t in v['spans_ticks'].items()},
            gain_vs_same_workload_budget=v['tokens_per_second']/ref['tokens_per_second']-1,
            bus_bytes_per_token=(v['read_bus_bytes']+v['write_bus_bytes'])/nt,
            max_outstanding_descriptors=v['max_outstanding_descriptors'],
            max_outstanding_beats=v['max_outstanding_beats'],
            max_descriptor_queue=v['max_descriptor_queue'],S_peak=v['P_scratch_peak_bytes']))
    def get(bw,q,release):return next(c for c in cases if c['name']==f'decode512-bw{bw}-q{q}-release{release}')
    base,queue,best=get(102400,0,0),get(102400,1,0),get(102400,1,2)
    # Potential only: S16 stream/LC conversion is NOT qualified for this S32 trace.
    chunks=36*11008//64;old_g_ms=chunks*861/300000;stream_g_ms=chunks*37/300000
    result=dict(passed=True,source_commit=r['source_commit'],Slurm_job=r['Slurm_job'],
        packages=3,verified_members=members,cases=cases,
        default_exact_full_RESULT_regression=True,
        rejected_experiment=dict(run='15',reason='release2 used S/B reservation end before adapter/core finished consuming input; not an accepted implementation or performance result'),
        native_G=r['native-g'],native_G_rendezvous=r['rendezvous'],
        queue_policy_saved_ms=base['ms_per_token']-queue['ms_per_token'],
        consume_release_extra_saved_ms=queue['ms_per_token']-best['ms_per_token'],
        total_saved_ms=base['ms_per_token']-best['ms_per_token'],
        speedup=best['tokens_s']/base['tokens_s']-1,
        remaining_ms_to_10tok_s=best['ms_per_token']-100,
        conditional_G_potential=dict(eligible_for_whole_model=False,SiLU_values=36*11008,
            old_service_ms=old_g_ms,measured_native_stream_ms=stream_g_ms,
            adapter_conversion_memory_overlap_and_quality_excluded=True,
            unsupported_best_case_tokens_s=1000/(best['ms_per_token']-old_g_ms+stream_g_ms)),
        native_G_admission=r['native_G_whole_model_admission'],FFN_admission=r['full_FFN_one_pass_admission'],
        native_full_model_tokens_s=None,energy_J_token=None,production_RTL_modified=False,
        full_model_numeric_replay=False,physical_clock_qualified=False)
    (root/'summary.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return {k:result[k] for k in ('passed','packages','verified_members','speedup','total_saved_ms','remaining_ms_to_10tok_s')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    print(json.dumps(summarize(p.parse_args().root)))
