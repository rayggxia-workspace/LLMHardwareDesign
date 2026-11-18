"""Independent frozen-input, frequency conversion, replacement and metric checks."""
from pathlib import Path
from hashlib import sha256
import json,math
H=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
d=load(H/'results.json');checks=[]
def eq(a,b,label):
    assert math.isclose(a,b,rel_tol=2e-9,abs_tol=1e-12),(label,a,b)
    checks.append(label)
for rel,h in d['input_sha256'].items():assert sha256((H/'inputs'/rel).read_bytes()).hexdigest()==h,rel
assert d['sram_bits']==512 and d['p_lanes']==3 and d['ddr_period_ps']==630 and not d['new_simulation_jobs']
B='work/Melodydt/280';T='work/Melodydt/293'
pf={x['model']:x for x in load(H/'inputs'/T/'prefill-energy-300-v3/results.json')['models']}
bound_receipts=0
for model in d['models']:
    m=model['model'];ledger=load(H/'inputs'/B/'closure-v5/timing-ledger'/(m+'-decode.json'))
    for name in ('acceptance.json','ddr-window-energy.json'):
        rel='closure-v5/deployments/'+m+'-decode-e32-18/result/'+name
        expected={k.replace('\\','/'):v for k,v in ledger['inputs'].items()}[rel]
        assert d['input_sha256'][B+'/'+rel]==expected;bound_receipts+=1
for model in d['models']:
    m=model['model'];tm=model['timing']
    eq((sum(tm['position_200_ps'])+tm['head_200_ps'])*1e-12,model['windows']['prefill512']['frequencies']['200']['duration_s'],'sum 512 + one head')
    assert len(tm['position_200_ps'])==512
    for a,b,r in zip(pf[m]['timing']['position_ps'],tm['position_200_ps'],tm['position_ratio_200_300']):eq(a*r,b,'position migration')
    for phase,w in model['windows'].items():
        a,b=w['frequencies']['300'],w['frequencies']['200'];n=w['tokens']
        eq(b['duration_s']/a['duration_s'],w['time_ratio'],'time ratio')
        for scope in ('on_chip','on_chip_plus_ddr'):
            # 300 MHz is unchanged from the latest accepted source / R candidate.
            if m in ('qwen35','falcon'):
                r=next(x for x in load(H/'inputs'/B/'recurrent-300mhz/candidate-rollup.json')['models'] if x['model']==m)
                expect=r['windows'][phase]['dma_candidate_envelope'][scope]['energy_j_per_window']
            elif phase=='prefill512':
                ss=pf[m][phase]['dma_scenarios'];expect=[min(s['scopes'][scope]['energy_j_per_window'][0] for s in ss.values()),max(s['scopes'][scope]['energy_j_per_window'][1] for s in ss.values())]
            else:
                # Read the unmodified source ledger, independently of the builder.
                src=H/'inputs'/B/'closure-v5/dma-ledger'/(m+'-decode.json')
                ss=load(src)['scenarios'];field='estimated_'+scope
                expect=[min(s['windows']['decode'][field]['energy_nj_per_window'][0]*1e-9 for s in ss.values()),max(s['windows']['decode'][field]['energy_nj_per_window'][1]*1e-9 for s in ss.values())]
            for i in (0,1):eq(a['scopes'][scope]['energy_j_per_window'][i],expect[i],'300 unchanged')
        dc=w['ddr'];eq(a['ddr_j'],dc['command_300_j']+dc['background_300_j'],'DDR300 split')
        eq(b['ddr_j'],dc['command_300_j']*dc['command_ratio']+dc['background_300_j']*dc['background_power_ratio']*w['time_ratio'],'DDR200 distinct command/background')
        for k,rule in w['transfer_rules'].items():
            if k.startswith('proxy_') and k not in a['components_j']:continue
            for i in (0,1):
                av,bv=a['components_j'][k][i],b['components_j'][k][i]
                factor=w['time_ratio']*rule['power_ratio'][i] if rule['kind']=='residence' else rule.get('energy_ratio',1.)
                eq(bv,av*factor,'component '+k)
        for freq,x in w['frequencies'].items():
            t=x['duration_s'];eq(x['tokens_per_second']*t,n,'throughput')
            chip=[math.fsum(v[i] for v in x['components_j'].values()) for i in (0,1)]
            for i in (0,1):eq(chip[i],x['base_on_chip_j'][i],'component conservation')
            if x['recurrent']:
                r=x['recurrent'];assert r['removed_term'] not in x['components_j'];assert r['service_time_s']<t
                key='falcon-wide' if m=='falcon' else m;sub='recurrent-300mhz' if freq=='300' else 'recurrent-step1'
                cal=load(H/'inputs'/B/sub/(key+'-calibration.json'))
                s=[v for v in cal['windows'] if v['segment']['window']==('prefill' if phase=='prefill512' else phase)]
                group=[sum(v['increment_nj'] for v in s if v['segment']['group']==g)*1e-9 for g in (0,1)]
                idles=[v['power_w']['idle']['total'] for v in s]
                for i,op in [(0,min),(1,max)]:
                    eq(x['components_j']['recurrent_dynamic'][i],op(group)*r['calls_16channel'],'R same-frequency active')
                    eq(x['components_j']['recurrent_idle'][i],op(idles)*t,'one R residence')
                    eq(chip[i],x['before_recurrent_on_chip_j'][i]-r['removed_energy_j'][i]+sum(x['components_j'][k][i] for k in ('recurrent_dynamic','recurrent_idle','recurrent_injection')),'R replace not add')
            assert len(x['dma_scenarios'])==4
            for name,sc in x['dma_scenarios'].items():
                for i in (0,1):
                    eq(sc['idle_j'][i],d['dma_idle_transfer'][name][freq][i]*t,'DMA idle')
                    eq(sc['dma_energy_j'][i],sc['idle_j'][i]+sc['dynamic_j'][i],'one DMA total')
                    eq(sc['scopes']['on_chip']['energy_j_per_window'][i],chip[i]+sc['dma_energy_j'][i],'one DMA only')
                    eq(sc['scopes']['on_chip_plus_ddr']['energy_j_per_window'][i],chip[i]+sc['dma_energy_j'][i]+x['ddr_j'],'DDR add once')
            for scope,met in x['scopes'].items():
                for i,op in [(0,min),(1,max)]:
                    e=op(sc['scopes'][scope]['energy_j_per_window'][i] for sc in x['dma_scenarios'].values())
                    eq(met['energy_j_per_window'][i],e,'mutually exclusive envelope')
                    eq(met['energy_mj_per_token'][i]*n/1000,e,'mJ/token')
                    eq(met['average_power_w'][i]*t,e,'power')
                    eq(met['tokens_per_joule'][1-i]*e,n,'tokens/J')
                assert met['energy_j_per_window'][0]<=met['energy_j_per_window'][1]
result=dict(passed=True,models=7,frequency_windows=28,numeric_checks=len(checks),frozen_inputs=len(d['input_sha256']),server_receipts_bound_to_published_ledger_sha=bound_receipts,results_sha256=sha256((H/'results.json').read_bytes()).hexdigest(),new_simulation=False,full_sequence_error_validated=False,checks=checks)
(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='checks'})
