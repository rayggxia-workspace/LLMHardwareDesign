"""Independent 300 MHz replacement, units, unchanged DDR and coverage audit."""
from pathlib import Path
from hashlib import sha256
import json,math,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(p):return json.loads(p.read_bytes())
def main():
    data=load(HERE/'candidate-rollup.json');checks=[]
    def eq(a,b,label):
        assert math.isclose(a,b,rel_tol=2e-10,abs_tol=1e-12),(label,a,b)
        checks.append(label)
    for rel,h in data['input_sha256'].items():
        p=HERE/'inputs'/rel
        if not p.exists():p=ROOT/rel
        assert sha256(p.read_bytes()).hexdigest()==h,rel
    assert data['core_period_ps']==3334 and data['sram_bits']==512
    assert not data['timing_recomputed_for_candidate_service'] and not data['full_model_numeric_accepted']
    annotated=0
    for model in data['models']:
        key='qwen35' if model['model']=='qwen35' else 'falcon-wide'
        cal=load(HERE/(key+'-calibration.json'))
        for ident,s in enumerate(cal['windows']):
            for name in ('active','idle'):
                p=HERE/'results'/key/f'window-{ident}-{name}.json';r=load(p)
                log=p.with_suffix('.log');assert sha256(log.read_bytes()).hexdigest()==r['log_sha256']
                txt=log.read_text();a=re.findall(r'Annotated (\d+) pin activities\.',txt)
                assert a==[str(cal['expected_annotated_pins'])]
                assert r['power_w']==s['power_w'][name]
                eq(r['retiming']['target_window_ps'],r['retiming']['source_window_ps']*3334/5000,'clock timebase')
                annotated+=1
        for phase,w in model['windows'].items():
            t,n=w['duration_s'],w['tokens'];eq(w['tokens_per_second']*t,n,'unchanged throughput')
            samples=[s for s in cal['windows'] if s['segment']['window']==w['sample_phase']]
            group=[sum(s['increment_nj'] for s in samples if s['segment']['group']==g)*1e-9 for g in (0,1)]
            for i in (0,1):eq(w['increment_j_per_16channel'][i],group[i],'group pair')
            idles=[s['power_w']['idle']['total'] for s in samples]
            expected=[w['calls_16channel']*min(group)+t*min(idles)+w['retained_injection_proxy_j'][0],w['calls_16channel']*max(group)+t*max(idles)+w['retained_injection_proxy_j'][1]]
            for i in (0,1):eq(expected[i],w['replacement_j'][i],'state replacement')
            assert w['one_r_active_time_s']<=t
            if key=='falcon-wide':
                for i,factor in [(0,.5),(1,2.)]:eq(w['retained_injection_proxy_j'][i],w['calls_16channel']*16*data['multiply_proxy_nj'][i]*factor*1e-9,'Falcon injection retained')
            else:assert w['retained_injection_proxy_j']==[0.,0.]
            alternatives=[('base',w['baseline'],w['candidate']),('special',w['special_baseline'],w['special_candidate'])]
            for variant in w['dma_baseline']:
                alternatives += [('dma/'+variant,w['dma_baseline'][variant],w['dma_candidate'][variant]),('special-dma/'+variant,w['special_dma_baseline'][variant],w['special_dma_candidate'][variant])]
            for label,before,after in alternatives:
                for scope in ('on_chip','on_chip_plus_ddr'):
                    b,a=before[scope],after[scope]
                    assert a['energy_j_per_window'][0]<=a['energy_j_per_window'][1]
                    for i in (0,1):
                        e=a['energy_j_per_window'][i]
                        eq(e,b['energy_j_per_window'][i]-w['removed_proxy_j'][i]+expected[i],label+'/no double count')
                        eq(e,a['energy_j_per_token'][i]*n,label+'/Jtoken')
                        eq(e,a['energy_mj_per_token'][i]*n/1000,label+'/mJtoken')
                        eq(e,a['average_power_w'][i]*t,label+'/W')
                        eq(e*a['tokens_per_joule'][1-i],n,label+'/tokensJ')
                for i in (0,1):eq(after['on_chip_plus_ddr']['energy_j_per_window'][i]-after['on_chip']['energy_j_per_window'][i],before['on_chip_plus_ddr']['energy_j_per_window'][i]-before['on_chip']['energy_j_per_window'][i],label+'/DDR unchanged')
            for i in (0,1):
                for scope in ('on_chip','on_chip_plus_ddr'):
                    endpoint=(min if i==0 else max)(s[scope]['energy_j_per_window'][i] for s in w['dma_candidate'].values())
                    eq(endpoint,w['dma_candidate_envelope'][scope]['energy_j_per_window'][i],'mutually exclusive envelope')
            for label,before,after in [('base',w['baseline'],w['candidate']),('including_read_dma',w['dma_baseline_envelope'],w['dma_candidate_envelope'])]:
                width=lambda d:d['on_chip']['energy_j_per_window'][1]-d['on_chip']['energy_j_per_window'][0]
                eq((1-width(after)/width(before))*100,w['interval_width_reduction_percent'][label],'width shrink')
    assert annotated==48
    result=dict(passed=True,models=2,model_windows=8,paired_power_windows_verified=annotated,numeric_checks=len(checks),
        input_sha256_verified=len(data['input_sha256']),candidate_sha256=sha256((HERE/'candidate-rollup.json').read_bytes()).hexdigest(),
        checks=checks,full_model_numeric_accepted=False,physical_timing_signoff=False)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
