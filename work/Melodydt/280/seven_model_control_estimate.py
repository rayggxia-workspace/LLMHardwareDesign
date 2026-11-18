"""Extend v3 with audited control counts and clearly qualified C639 transfers."""
import copy
from hashlib import sha256
import json
from pathlib import Path
from six_model_tlm_power import metrics

HERE=Path(__file__).resolve().parent
MODELS=('qwen3','llama','granite','phi','gemma','qwen35','falcon')
def load(p):return json.loads(p.read_bytes())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def bounds(v):
    v=list(v);assert v and min(v)>=0
    return [min(v),max(v)]


def main():
    paths={k:HERE/'control-gap-results'/(k+'.json') for k in ('local','switch','mother-startup','mother-runtime','model-control-counts')}
    data={k:load(p) for k,p in paths.items()}
    macro=load(HERE/'no-wire-results/mother-pm.json')
    assert data['mother-runtime']['parameters']['SERVICE_STALL_LIMIT'][1]==2000000
    assert data['mother-startup']['parameters']==data['mother-runtime']['parameters']
    assert data['mother-startup']['netlist_sha256']==data['mother-runtime']['netlist_sha256']
    for k in ('local','switch','mother-startup','mother-runtime'):
        assert data[k]['wire_parasitics_loaded'] is False and data[k]['clock_mhz']==300
    core=bounds(v['power_w']['total'] for name in ('mother-startup','mother-runtime') for v in data[name]['windows'].values())
    local=[0.,0.]
    for inst in data['local']['instances'].values():
        b=bounds(w['power_w']['total'] for w in inst['windows'].values())
        local=[a+c for a,c in zip(local,b)]
    switch=bounds(x['pj_per_handshake_cycle']/1000 for x in data['switch']['paired'])
    # The measured macro's conditional clock arc already represents read
    # access energy. Do not add its OpenSTA internal estimate a second time.
    pm=bounds(p['increment']['read']['exact_clock_arc_pj']/p['increment']['read']['requests']/1000 for p in macro['pages'])
    coefficients={'mother_core_w':core,'local_shell_dispatch_w':local,
                  'switch_nj_per_flit':switch,'mother_pm_nj_per_runtime_read':pm}
    for model in MODELS:
        prior=load(HERE/(model+'_tlm_power_v3_arithmetic.json'))
        baseline=load(HERE/(model+'_tlm_power_v2_no_wire.json'))
        out=copy.deepcopy(prior);out['scope']='Control-extended conditional estimate; C639 transfer, not complete physical-chip power'
        out['control_coefficients']=coefficients;out['previous_v3_sha256']=digest(HERE/(model+'_tlm_power_v3_arithmetic.json'))
        out['control_input_sha256']={str(p.relative_to(HERE)):digest(p) for p in list(paths.values())+[HERE/'no-wire-results/mother-pm.json',HERE/'control-count-input.json']}
        out['control_estimator_sha256']=digest(Path(__file__))
        out['control_assumptions']=[
            'Actual C639 reference has STALL_LIMIT=4096 and SERVICE_STALL_LIMIT=2000000; replace previous 4096 service-timeout core reference.',
            'Core power range includes two startup and six runtime windows and is applied once over the frozen duration. Startup is not added again; exact per-state residency is not measured.',
            'Four cut LC shells plus four actual C639 routers are assumed clocked for the full window. PM arrays and descriptor-fetch children are excluded. Per-model router registries and physical deployment remain unverified.',
            'Static control-page instruction counts reconcile to frozen calls/pages. One PM read per compact instruction, no fetch cache; four-flit CALL plus four-flit successful terminal. Cancellation/retry traffic is excluded.',
            'PM runtime reads use the accepted four-macro conditional clock energy (one addressed 128-bit control word). This is separate from the 512-bit data SRAM and does not change its width.',
            'All intervals are sampled coefficient/scenario endpoints, not confidence intervals or guaranteed error bounds. No wire RC is loaded.']
        out['not_included']=[
            'Mother image-install/sequence/cohort grant wrappers and packet bridges outside the calibrated core; unsampled startup states and exact state residency.',
            'Per-model router registry differences, actual instance/clock gating, global clock and inter-block physical interconnect.',
            'Read DMA idle/leakage and calibrated dynamic power; DDR PHY/package/board I/O. Read DMA dynamic proxy remains a separate scenario.',
            'Matched special-operator RTL numerical/power acceptance, old M timing closure and E32 9/18 cycle calibration; wire parasitics intentionally excluded.']
        for name,w in out['windows'].items():
            ref=baseline['windows'][name];cnt=data['model-control-counts']['models'][model][name]
            ps,tokens=w['elapsed_ps'],w['tokens']
            assert (ps,tokens)==(cnt['elapsed_ps'],cnt['tokens'])
            assert cnt['calls_by_site']==ref['top_level_service_calls_by_site']
            raw={
                'native_mother_core_actual_parameter_reference':[v*ps/1000 for v in core],
                'local_shell_dispatch_reference_4x':[v*ps/1000 for v in local],
                'mother_pm_runtime_fetch_increment':[v*cnt['instructions'] for v in pm],
                'cohort_switch_active_increment':[v*cnt['control_packet_flits'] for v in switch]}
            old=ref['components']['native_mother_core_reference_1x']['energy_nj_per_window']
            delta=[sum(v[e] for v in raw.values())-old[e] for e in (0,1)]
            assert 0<=delta[0]<=delta[1]
            w['prior_v3_on_chip']=copy.deepcopy(w['estimated_on_chip'])
            w['prior_v3_on_chip_plus_ddr']=copy.deepcopy(w['estimated_on_chip_plus_ddr'])
            w['replaced_native_mother_core']=copy.deepcopy(ref['components']['native_mother_core_reference_1x'])
            w['control_components']={k:metrics(v,ps,tokens) for k,v in raw.items()}
            w['control_net_increment']=metrics(delta,ps,tokens)
            w['control_counts']={k:cnt[k] for k in ('instructions','calls_by_site','control_packet_flits','plan_sha256','reported_plan_sha256','plan_binding')}
            for key in ('estimated_on_chip','estimated_on_chip_plus_ddr'):
                w[key]=metrics([v+delta[e] for e,v in enumerate(w[key]['energy_nj_per_window'])],ps,tokens)
            for sensitivity in w['read_dma_sensitivity'].values():
                for key in ('estimated_on_chip','estimated_on_chip_plus_ddr'):
                    sensitivity[key]=metrics([v+delta[e] for e,v in enumerate(sensitivity[key]['energy_nj_per_window'])],ps,tokens)
        (HERE/(model+'_tlm_power_v4_control.json')).write_bytes((json.dumps(out,indent=2)+'\n').encode())
        print(model,out['windows']['decode']['estimated_on_chip']['energy_mj_per_token'],out['windows']['decode']['estimated_on_chip_plus_ddr']['energy_mj_per_token'])
    (HERE/'control-gap-results/coefficients.json').write_bytes((json.dumps(coefficients,indent=2)+'\n').encode())


if __name__=='__main__':main()
