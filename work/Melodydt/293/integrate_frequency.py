"""Reconstruct whole-window timing and reintegrate the frozen covered subtotal."""
from pathlib import Path
import json, math, csv
from hashlib import sha256
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'280'
ORDER=['qwen3','llama','phi','gemma','granite','qwen35','falcon']
def load(p):return json.loads(p.read_bytes())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def key(s):return s['kind'],s['step'],s['layer']
def power_group(rows):
    rows=sorted(rows,key=lambda x:x['total'])
    return [rows[0],rows[-1]]
def resident_references():
    d={n:load(OLD/'no-wire-results'/(n+'.json')) for n in ['m','control','write_u','sram','legacy','mother-pm','native-mother']}
    def group(f,p):return power_group(v['power_w'] for k,v in d[f]['windows'].items() if p(k))
    r={
      'm_clocked_idle_3x':group('m',lambda k:'idle-' in k),
      's_p_clocked_idle_4x':group('sram',lambda k:k.endswith('__idle')),
      'lc_pm_loaded_quiet_4x':group('control',lambda k:k.startswith('pm-quiet__')),
      'write_dma_clocked_idle_1x':group('write_u',lambda k:k.startswith('real-span') and k.split('__')[-2].endswith('-1')),
      'pm_transport_clocked_idle_1x':group('write_u',lambda k:k.startswith('pm-real-length') and k.split('__')[-2].endswith('-1')),
      'g32_down_idle_1x':group('legacy',lambda k:'g32' in k and k.endswith('-down')),
      'cohort_switch_idle_1x':group('legacy',lambda k:'switch' in k),
      'native_mother_core_reference_1x':power_group(v['power_w'] for v in d['native-mother']['windows'].values()),
    }
    rows=[v['power_w'] for k,v in d['write_u']['windows'].items() if k.startswith('u-component') and k.endswith('__quiet')]
    r['u_add_chain_clocked_idle_1x']=[{k:sum(v[k] for v in rows) for k in rows[0]}]*2
    macro=d['mother-pm']['pages'][0]['cases']['read-quiet']['opensta_w']
    r['mother_pm_clocked_idle_4_macros']=[macro]*2
    counts=load(OLD/'qwen3_lc_fetch_power.json')['windows']
    groups=[]
    for site in range(4):
        groups.append(group('control',lambda k:k.startswith('lc-fetch-') and k.split('__')[-2].endswith('-site'+str(site)) and not any(counts[k.split('__')[-2]]['transactions'].values())))
    r['lc_descriptor_fetch_quiet_4x']=[{k:sum(g[e][k] for g in groups) for k in groups[0][0]} for e in (0,1)]
    return r
def ddr_parts(row):
    commands=background=0
    for ch in row['channels']:
        commands+=sum(v for k,v in ch['command_j'].items() if k not in ('ref_energy','refb_energy'))
        background+=sum(ch['command_j'].get(k,0) for k in ('ref_energy','refb_energy'))
        background+=sum(sum(r.values()) for r in ch['background_j_by_rank'].values())
    return commands,background
def metrics(e,t,n):
    return {'energy_j_per_token':[v/n for v in e],'average_power_w':[v/t for v in e],
            'tokens_per_joule':[n/e[1],n/e[0]],'energy_j_per_window':e}
def analyze(model,samples,meta,oldrow,refs):
    probe={phase:{p:{key(s):s for s in samples[phase,p]['segments']} for p in (3334,5000)} for phase in ('prefill','decode')}
    ratios={}; errors=[]; countchecks=[]; body={}; tail={}; weights={}; sensitivity={}
    for phase in ('prefill','decode'):
        a,b=probe[phase][3334],probe[phase][5000]
        assert a.keys()==b.keys()
        for k in a:
            # Integer transactions must remain identical under a pure clock change.
            for c in ('sram_by_site','service_calls','model_events'):
                assert a[k]['components'][c]==b[k]['components'][c],(model,phase,k,c)
            for x,y in zip(a[k]['ddr']['channels'],b[k]['ddr']['channels']):
                # DRAM command coalescing/row policy can change with arrival time;
                # completed logical transactions, unlike device commands, are invariant.
                for c in ('num_reads_done','num_writes_done'):
                    assert x['commands_and_completions'][c]==y['commands_and_completions'][c]
            ratios[phase,str(k)]=b[k]['elapsed_ps']/a[k]['elapsed_ps']
        frozen=meta[phase]['frozen']
        boundaries=[x['complete_ps'] for x in frozen['boundary']]
        retires=[x['time_ps'] for x in frozen['retirements']]
        for step in (0,1):
            basebody=boundaries[step]-(0 if step==0 else (boundaries[0] if phase=='prefill' else retires[0]))
            rows=[x for x in meta[phase]['timings'] if x['step']==step]
            sig={x['layer']:str(x['signature']) for x in meta[phase]['signatures'] if x['step']==step}
            chosen=[k[2] for k in a if k[0]=='layer' and k[1]==step]
            weighted=[]; lo=hi=0
            for row in rows:
                candidates=[l for l in chosen if sig[l]==sig[row['layer']]]
                assert candidates,('uncovered layer class',model,step,row['layer'])
                selected=min(candidates,key=lambda l:abs(l-row['layer']))
                k=('layer',step,selected)
                ratio=b[k]['elapsed_ps']/a[k]['elapsed_ps']
                weighted.append((k,row['elapsed_ps']))
                rr=[b['layer',step,l]['elapsed_ps']/a['layer',step,l]['elapsed_ps'] for l in candidates]
                lo+=row['elapsed_ps']*min(rr);hi+=row['elapsed_ps']*max(rr)
                if row['layer'] in chosen:
                    errors.append(abs(a[k]['elapsed_ps']/row['elapsed_ps']-1)*100)
            remainder=basebody-sum(x['elapsed_ps'] for x in rows)
            assert remainder>=0
            others=[('ingress',step,None)]
            if step==0:others.append(('boot',-1,None))
            if step==1 and phase=='prefill':others.append(('residual_read',0,None))
            if phase=='decode' and step==1:
                # No boot in retirement-to-retirement decoding.
                pass
            denom=sum(a[k]['elapsed_ps'] for k in others)
            other_ratio=sum(b[k]['elapsed_ps'] for k in others)/denom
            body[phase,step]=sum(t*b[k]['elapsed_ps']/a[k]['elapsed_ps'] for k,t in weighted)+remainder*other_ratio
            weights[phase,step]=weighted+[(k,remainder*a[k]['elapsed_ps']/denom) for k in others]
            sensitivity[phase,step]=[lo+remainder*other_ratio,hi+remainder*other_ratio]
            if phase=='decode':
                k=('head',step,None)
                tail[step]=(retires[step]-boundaries[step])*b[k]['elapsed_ps']/a[k]['elapsed_ps']
                weights[phase,step].append((k,retires[step]-boundaries[step]))
        countchecks.append(phase)
    short=sum(body['prefill',s] for s in (0,1))
    dec=body['decode',1]+tail[1]
    p1=body['prefill',0];low=body['prefill',1];high=body['decode',1]
    p512=p1+511*low+(510*511//2)*(high-low)/512+tail[1]
    speed={'short_prefill_input_tok_s':2e12/short,'decode_tok_s':1e12/dec,
           'estimated_input_tok_s_to_logits':512e12/p512,'short_prefill_ms':short/1e9,
           'decode_interval_ms':dec/1e9,'estimated_prefill_to_logits_s':p512/1e12,
           'first_prefill_including_boot_ms':p1/1e9,'second_prefill_increment_ms':low/1e9,
           'decode_second_body_ms':high/1e9,'decode_tail_ms':tail[1]/1e9,
           'representative_300_vs_original_max_percent':max(errors),
           'whole_model_200_error_percent':None,'full_prefill512_error_percent':None,
           'inherited_attention_nonlinearity_percent':oldrow['speed']['component_max_deviation_percent']}
    energy=load(OLD/(model+'_tlm_power_v2_no_wire.json'));windows={}
    for phase in ('prefill','decode'):
        original=energy['windows'][phase]
        newtime=(short if phase=='prefill' else dec)/1e12
        oldtime=original['elapsed_ps']/1e12;rt=newtime/oldtime
        ws=weights[phase,0]+weights[phase,1] if phase=='prefill' else weights[phase,1]
        # Restore full-window weighting from original whole-layer elapsed times.
        cmd=[]; bg=[]
        for period in (3334,5000):
            cs=bs=0
            for k,t in ws:
                row=probe[phase][period][k]
                cc,bb=ddr_parts(row['ddr'])
                scale=t/probe[phase][3334][k]['elapsed_ps']
                cs+=cc*scale;bs+=bb*scale
            cmd.append(cs);bg.append(bs)
        dratios=[cmd[1]/cmd[0],bg[1]/bg[0]]
        stagepath=OLD/('qwen3-ddr-results' if model=='qwen3' else 'six-model-results/'+model)/phase/'ddr-window-energy.json'
        if model=='qwen3':
            import sys
            sys.path.insert(0,str(OLD))
            from ddr_window_energy import snapshot,window
            marks=('start','prefill_end') if phase=='prefill' else ('retire_1','retire_2')
            paths=[ROOT/'results'/('qwen3-'+phase+'-'+m+'.json') for m in marks]
            oldddr=window(snapshot(paths[0]),snapshot(paths[1]),2 if phase=='prefill' else 1)
            source_label='task293/results/qwen3-'+phase+'-*.json'
        else:
            oldddr=load(stagepath)['windows'][phase]
            source_label=str(stagepath.relative_to(OLD))
        assert math.isclose(oldddr['device_j'],original['components']['ddr_devices']['energy_nj_per_window'][0]/1e9,rel_tol=1e-10)
        oc,ob=ddr_parts(oldddr)
        ddr=oc*dratios[0]+ob*dratios[1]
        components={}; split={};mcheck=[]
        for name,v in original['components'].items():
            e=[x/1e9 for x in v['energy_nj_per_window']]
            if name=='ddr_devices':components[name]=[ddr,ddr];continue
            if name in refs:
                fractions=[p['leakage']/p['total'] for p in refs[name]]
                components[name]=[e[i]*rt*((1-fractions[i])*2/3+fractions[i]) for i in (0,1)]
                split[name]={'leakage_fraction_300':fractions,'time_ratio':rt,'dynamic_power_ratio':2/3}
            elif name in ('m_busy_increment','m_ordinary_projection_increment'):
                field='modeled_m_by_site' if name=='m_busy_increment' else 'ordinary_projection_m_by_site'
                busy=[]
                for period in (3334,5000):
                    busy.append(sum(t/probe[phase][3334][k]['elapsed_ps']*sum(x.get('busy_interval_union_ps',0) for x in probe[phase][period][k]['components'][field]) for k,t in ws))
                ratio=(busy[1]/busy[0])*2/3 if busy[0] else 1
                components[name]=[x*ratio for x in e];mcheck.append(ratio)
            else:components[name]=e
        chip=[sum(v[e] for k,v in components.items() if k!='ddr_devices') for e in (0,1)]
        total=[x+ddr for x in chip];n=original['tokens']
        windows[phase]={'tokens':n,'duration_s':newtime,'tokens_per_second':n/newtime,
            'scopes':{'on_chip':metrics(chip,newtime,n),'on_chip_plus_ddr':metrics(total,newtime,n)},
            'components_j':components,'resident_reintegration':split,'ddr_reintegration':{
                'source':source_label,'command_ratio':dratios[0],'background_refresh_ratio':dratios[1],
                'original_command_j':oc,'original_background_refresh_j':ob,'estimated_j':ddr},
            'm_increment_energy_ratios':mcheck,'event_energy_assumption':'same accepted event counts; unchanged event coefficients at fixed V and temperature'}
    return {'model':model,'name':oldrow['name'],'speed':speed,'windows':windows,
            'baseline_300':{'speed':{k:oldrow['speed'][k] for k in ('short_prefill_input_tok_s','decode_tok_s','estimated_input_tok_s_to_logits')},'windows':oldrow['windows']},
            'selected_layers':samples['prefill',3334]['selected_layers'],'numerical_layer_checks':sum(len(s['numerical']) for s in samples.values()),
            'passed_frequency_transaction_checks':countchecks,'not_included':energy['not_included'],
            'speed_ratio_sensitivity':{str(k):v for k,v in sensitivity.items()},
            'sample_paths':[s['_path'] for s in samples.values()]}
def main():
    frozen=ROOT.parent/'291/combined-results.json'
    assert sha(frozen)=='741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9'
    repo=ROOT.parents[2]
    for entry in load(ROOT.parent/'291/combined-inputs.json')['inputs']:
        assert sha(repo/entry['path'])==entry['sha256'],('changed frozen input',entry['path'])
    for m in ORDER:
        prior=load(OLD/(m+'_tlm_power_v2_no_wire.json'))
        for name,value in prior['input_sha256'].items():
            if name.startswith('no-wire-results/'):
                assert sha(OLD/name)==value,('changed calibration',name)
    old={x['model']:x for x in load(frozen)['models']};meta=load(ROOT/'baseline-metadata.json');refs=resident_references()
    index=defaultdict(dict)
    for p in sorted((ROOT/'results').glob('run-*/*/samples.json')):
        x=load(p);assert x['passed'];x['_path']=str(p.relative_to(ROOT));index[x['model']][x['phase'],x['core_ps']]=x
    result={'clock_mhz':200,'core_period_ps':5000,'ddr_period_ps':630,'fixed_voltage_temperature':True,'scope':'conditional covered subtotal, no wire parasitics',
            'baseline_sha256':sha(frozen),'models':[],'missing_models':[],'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'results').glob('run-*/*/samples.json')}}
    for m in ORDER:
        if len(index[m])!=4:result['missing_models'].append(m);continue
        row=analyze(m,index[m],meta[m],old[m],refs);result['models'].append(row)
        print(m,'speed',*[round(row['speed'][k],4) for k in ('short_prefill_input_tok_s','estimated_input_tok_s_to_logits','decode_tok_s')],flush=True)
    (ROOT/'results-200mhz.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'summary-200mhz.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['model','short_prefill_tok_s','estimated_512_prefill_tok_s','decode_tok_s','phase','scope','W_low','W_high','J_per_token_low','J_per_token_high','token_per_J_low','token_per_J_high'])
        for r in result['models']:
            for phase,v in r['windows'].items():
                for scope,e in v['scopes'].items():w.writerow([r['name']]+[r['speed'][k] for k in ('short_prefill_input_tok_s','estimated_input_tok_s_to_logits','decode_tok_s')]+[phase,scope]+e['average_power_w']+e['energy_j_per_token']+e['tokens_per_joule'])
if __name__=='__main__':main()
