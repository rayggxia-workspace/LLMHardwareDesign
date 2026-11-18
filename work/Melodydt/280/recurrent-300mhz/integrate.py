"""Replace only recurrent-state proxies in frozen latest 300 MHz ledgers."""
from pathlib import Path
from hashlib import sha256
import json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE='work/Melodydt/280'
def load(p):return json.loads(p.read_bytes())
def metrics(e,t,n):
    assert 0<e[0]<=e[1] and t>0 and n>0
    return dict(energy_j_per_window=e,energy_j_per_token=[v/n for v in e],energy_mj_per_token=[v*1000/n for v in e],average_power_w=[v/t for v in e],tokens_per_joule=[n/e[1],n/e[0]])
def main():
    manifest=load(HERE/'input-manifest.json');inputs={}
    for rel,x in manifest['files'].items():
        p=HERE/'inputs'/rel;assert sha256(p.read_bytes()).hexdigest()==x['sha256'];inputs[rel]=x['sha256']
    def read(rel):assert rel in inputs;return load(HERE/'inputs'/rel)
    baseline=read('output/pdf/seven-model-sync06-20261118-r2/frequency-estimates.json')
    prefill=read('work/Melodydt/293/prefill-energy-300-v3/results.json')
    oldroll=read(BASE+'/recurrent-step1/candidate-rollup.json')
    bindings=read(BASE+'/recurrent-step1/input-bindings.json');tb=read(BASE+'/recurrent-step1/calibration-tb-check.json')
    graph=read(BASE+'/recurrent-step1/signed-graph-audit.json')
    mult=[]
    for rel in inputs:
        if '/arithmetic-calibration-results/power-' in rel:
            d=read(rel)
            for s in d['samples']:mult.append(s['incremental_nj']/(4*s['packets']))
    assert mult;mul=[min(mult),max(mult)];models=[];checks=[]
    for model,key,term in [('qwen35','qwen35','proxy_gdn_state'),('falcon','falcon-wide','proxy_mamba_state')]:
        path=HERE/(key+'-calibration.json');cal=load(path);inputs[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes()).hexdigest()
        oldcal=read(BASE+'/recurrent-step1/'+key+'-calibration.json')
        assert cal['source_calibration_sha256']==inputs[BASE+'/recurrent-step1/'+key+'-calibration.json']
        assert cal['clock_mhz']==300 and cal['core_period_ps']==3334 and not cal['wire_parasitics_loaded']
        assert cal['source']['netlist_sha256']==oldcal['source']['netlist_sha256']
        assert cal['pin_graph']==oldcal['pin_graph'] and len(cal['windows'])==12
        assert next(x for x in graph if x['model']==key+'-fast')['passed']
        checkpoint=read(BASE+'/recurrent-step1/results/'+key+'/power/gate-replay-receipt.json')
        for name in ('commands.txt','segments.json'):
            assert next(v for k,v in checkpoint['inputs'].items() if Path(k).name==name)==bindings[key][name]['server_lf_sha256']
        for i,(a,b) in enumerate(zip(cal['windows'],oldcal['windows'])):
            assert a['segment']==b['segment'] and a['window_ps']*5000==b['window_ps']*3334
            for name in ('active','idle'):
                assert a['power_w'][name]['annotated']==cal['expected_annotated_pins']
                assert a['retiming'][name]['event_sequence_preserved'] and a['retiming'][name]['target_window_ps']==a['window_ps']
            assert math.isclose(a['increment_nj'],(a['power_w']['active']['total']-a['power_w']['idle']['total'])*a['window_ps']/1000,rel_tol=1e-12)
        original=read(BASE+'/'+model+'_tlm_power_v3_arithmetic.json');case=next(x for x in prefill['models'] if x['model']==model)
        record=dict(model=model,name=case['name'],proxy_removed=term,calibration_sha256=inputs[path.relative_to(ROOT).as_posix()],windows={})
        for phase in ('prefill','first_token','decode','prefill512'):
            sample_phase='prefill' if phase=='prefill512' else phase
            factor=256 if phase=='prefill512' else 1
            calls=sum(x['calls'] for x in original['windows'][sample_phase]['operation_audit'] if term[6:] in x['signature'])*factor
            assert calls>0
            if phase=='prefill512':
                w=case['prefill512'];t=w['duration_s'];n=w['tokens'];proxy=w['components_j'][term]
                assert all(math.isclose(proxy[i],case['short_prefill']['components_j'][term][i]*256,rel_tol=1e-12) for i in (0,1))
                basescopes=w['scopes'];dma={k:v['scopes'] for k,v in w['dma_scenarios'].items()}
                special=w['special_candidate']['scopes'];specialdma=w['special_candidate']['dma_scenarios']
            else:
                stage='prefill' if phase=='prefill' else 'decode'
                ledger=read(BASE+'/closure-v5/timing-ledger/'+model+'-'+stage+'.json')
                dledger=read(BASE+'/closure-v5/dma-ledger/'+model+'-'+stage+'.json')
                sledger=read(BASE+'/closure-v5/special-candidate-ledger/'+model+'-'+stage+'.json')
                accept=read(BASE+'/closure-v5/deployments/'+model+'-'+stage+'-e32-18/result/acceptance.json')
                assert accept['passed'] and accept['numerical_files_equal'] and accept['numerical_and_traffic_invariants_equal']
                w=ledger['windows'][phase];s=sledger['windows'][phase];assert term not in s['removed_proxies']
                t=w['elapsed_ps']/1e12;n=w['tokens'];proxy=[v*1e-9 for v in w['components'][term]['energy_nj_per_window']]
                assert w['components'][term]['energy_nj_per_window']==original['windows'][phase]['arithmetic_components'][term]['energy_nj_per_window']
                def conv(z):return {scope:metrics([v*1e-9 for v in z[k]['energy_nj_per_window']],t,n) for scope,k in [('on_chip','estimated_on_chip'),('on_chip_plus_ddr','estimated_on_chip_plus_ddr')]}
                basescopes=conv(w);dma={k:conv(v['windows'][phase]) for k,v in dledger['scenarios'].items()};special=conv(s);specialdma={k:conv(v) for k,v in s['dma_scenarios'].items()}
            samples=[v for v in cal['windows'] if v['segment']['window']==sample_phase];assert len(samples)==4
            increments=[];durations=[]
            for group in (0,1):
                pair=[s for s in samples if s['segment']['group']==group];assert sorted(s['segment']['lane0'] for s in pair)==[0,8]
                increments.append(sum(s['increment_nj'] for s in pair)*1e-9)
                durations.append(sum(s['window_ps'] for s in pair)*1e-12)
            idle=[s['power_w']['idle']['total'] for s in samples]
            active=max(durations)*calls;assert active<=t
            injection=[0.,0.] if model=='qwen35' else [calls*16*mul[0]*.5e-9,calls*16*mul[1]*2e-9]
            replacement=[calls*min(increments)+t*min(idle)+injection[0],calls*max(increments)+t*max(idle)+injection[1]]
            def replace(scopes):return {k:metrics([v['energy_j_per_window'][i]-proxy[i]+replacement[i] for i in (0,1)],t,n) for k,v in scopes.items()}
            candidate=replace(basescopes);candidate_dma={k:replace(v) for k,v in dma.items()}
            def envelope(scenarios):return {scope:metrics([min(v[scope]['energy_j_per_window'][0] for v in scenarios.values()),max(v[scope]['energy_j_per_window'][1] for v in scenarios.values())],t,n) for scope in basescopes}
            oldenv=envelope(dma);newenv=envelope(candidate_dma)
            reductions={}
            for label,before,after in [('base',basescopes,candidate),('including_read_dma',oldenv,newenv)]:
                width=lambda s:s['on_chip']['energy_j_per_token'][1]-s['on_chip']['energy_j_per_token'][0]
                reductions[label]=(1-width(after)/width(before))*100
            record['windows'][phase]=dict(tokens=n,duration_s=t,tokens_per_second=n/t,calls_16channel=calls,
                sample_phase=sample_phase,prefill_activity_assumption='cold-state extrapolation' if 'prefill' in phase else 'captured history state',
                increment_j_per_16channel=increments,shared_r_idle_w=[min(idle),max(idle)],one_r_active_time_s=active,
                service_fraction=active/t,removed_proxy_j=proxy,replacement_j=replacement,retained_injection_proxy_j=injection,
                baseline=basescopes,candidate=candidate,dma_baseline=dma,dma_candidate=candidate_dma,
                dma_baseline_envelope=oldenv,dma_candidate_envelope=newenv,
                special_baseline=special,special_candidate=replace(special),
                special_dma_baseline=specialdma,special_dma_candidate={k:replace(v) for k,v in specialdma.items()},
                interval_width_reduction_percent=reductions)
            for i in (0,1):
                assert math.isclose(candidate['on_chip_plus_ddr']['energy_j_per_window'][i]-candidate['on_chip']['energy_j_per_window'][i],basescopes['on_chip_plus_ddr']['energy_j_per_window'][i]-basescopes['on_chip']['energy_j_per_window'][i],rel_tol=1e-12)
            checks.append(model+'/'+phase)
        models.append(record)
    result=dict(version='300 MHz v5 recurrent candidate 1',source=load(HERE/'source.json'),core_period_ps=3334,sram_bits=512,
        scope='conditional one shared 8-lane R; latest v5 timing and DDR unchanged; four mutually exclusive DMA scenarios',
        full_model_numeric_accepted=False,physical_binding_accepted=False,timing_recomputed_for_candidate_service=False,
        limits=['Two early channel groups per phase, no independent-layer coverage','Prefill activity cold-state only; complete512 execution/error unvalidated','FP32 conversion/provider and global interconnect not calibrated','Falcon injection keeps scalar proxy; no new physical timing qualification'],
        multiply_proxy_nj=mul,input_sha256=inputs,models=models)
    (HERE/'candidate-rollup.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'integrated_windows':checks,'decode':{m['model']:m['windows']['decode']['dma_candidate_envelope'] for m in models}},indent=2))

if __name__=='__main__':main()
