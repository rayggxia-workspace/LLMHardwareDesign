"""Refresh two frequencies from v5; legacy frequency response is an explicit estimate."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone,timedelta
import json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];B='work/Melodydt/280';T='work/Melodydt/293'
ORDER=['qwen3','llama','granite','phi','gemma','qwen35','falcon'];SOURCES={}
def read(rel):
    snapshot=HERE/'inputs'/rel
    if snapshot.exists():p=snapshot
    else:
        p=ROOT/rel;snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(p.read_bytes())
    data=p.read_bytes();SOURCES[rel]=sha256(data).hexdigest();return json.loads(data)
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def eq(a,b):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-12),(a,b)
def scaled(a,k):return [v*k for v in a]
def sums(d):return [math.fsum(v[i] for v in d.values()) for i in (0,1)]
def metric(e,t,n):return dict(energy_j_per_window=e,energy_mj_per_token=[v*1000/n for v in e],average_power_w=[v/t for v in e],tokens_per_joule=[n/e[1],n/e[0]])
def ddr_parts(row):
    cmd=bg=0.
    for c in row['channels']:
        cmd+=sum(v for k,v in c['command_j'].items() if k not in ('ref_energy','refb_energy'))
        bg+=sum(c['command_j'].get(k,0) for k in ('ref_energy','refb_energy'))+sum(sum(x.values()) for x in c['background_j_by_rank'].values())
    eq(cmd+bg,row['device_j']);return cmd,bg
def rows(d):return {m['model']:m for m in d['models']}
def power200(p):return p['leakage']+(p['total']-p['leakage'])*2/3
def main():
    p300=read(T+'/prefill-energy-300-v3/results.json');p=rows(p300)
    uniform={m['model']:m for m in p300['uniform_v4_reference']}
    oldspeed=rows(read(T+'/results-200mhz.json'));curve300=rows(read(T+'/prefill-v2/results.json'));curve200=rows(read(T+'/prefill-v3/results.json'))
    oldpower=read(T+'/power-v4/results.json');energy200=rows(oldpower)
    r300=read(B+'/recurrent-300mhz/candidate-rollup.json');rmodels=rows(r300)
    source=read(B+'/recurrent-300mhz/source.json')
    assert source['baseline_commit']==p300['parent_new_local_data_commit']=='e29d72a585dd1fb0cde6c9a6976ef0fe78f98f96'
    periphery=read(B+'/closure-v5/control-periphery-calibration.json')
    pp=sorted([v['power_w'] for v in periphery['windows'].values()],key=lambda x:x['total']);pp=[pp[0],pp[-1]]
    dma_coefs=read(B+'/closure-v5/dma-coefficients.json');dma_powers={}
    for name,c in dma_coefs.items():
        cal=read(B+'/closure-v5/dma-'+name+'-pin-calibration.json')
        assert SOURCES[B+'/closure-v5/dma-'+name+'-pin-calibration.json']==c['calibration_sha256']
        z=sorted([v['power_w'] for k,v in cal['windows'].items() if k.startswith('idle-')],key=lambda x:x['total']);z=[z[0],z[-1]]
        for i in (0,1):eq(z[i]['total'],c['idle_w'][i])
        dma_powers[name]={'300':[x['total'] for x in z],'200':[power200(x) for x in z], 'leakage':[x['leakage'] for x in z]}
    control=oldpower['control_frequency_transfer'];ar=oldpower['arithmetic_idle_calibration']
    ar300=sum(x['w300']*x['instances'] for x in ar.values());ar200=sum(x['w200']*x['instances'] for x in ar.values())
    out=[]
    for m in ORDER:
        case=p[m];dec=read(B+'/closure-v5/timing-ledger/'+m+'-decode.json')['windows']['decode']
        read(B+'/closure-v5/dma-ledger/'+m+'-decode.json')
        rawddr=read(B+'/closure-v5/deployments/'+m+'-decode-e32-18/result/ddr-window-energy.json')['windows']['decode']
        acceptance=read(B+'/closure-v5/deployments/'+m+'-decode-e32-18/result/acceptance.json');assert acceptance['passed'] and acceptance['numerical_files_equal']
        original=read(B+'/'+m+'_tlm_power_v2_no_wire.json')
        old=oldspeed[m];old3=curve300[m]['clocks']['300MHz'];old2=curve200[m]
        pos=case['timing']['position_ps'];head=case['timing']['head_ps'];assert len(pos)==512
        ratios=[b/a for a,b in zip(old3['per_position_body_ps'],old2['per_position_body_ps'])]
        pos200=[a*r for a,r in zip(pos,ratios)];headratio=old2['head_ps']/old3['final_head_ps'];h200=head*headratio
        tp=(sum(pos200)+h200)*1e-12
        rd=old['windows']['decode']['duration_s']/(original['windows']['decode']['elapsed_ps']*1e-12)
        td=dec['elapsed_ps']*1e-12*rd
        # Alternative migration: legacy 200 curve plus v5-v4 time deltas at core period ratio.
        additive=(sum(b+(a-c)*5000/3334 for a,b,c in zip(pos,old2['per_position_body_ps'],old3['per_position_body_ps']))+old2['head_ps']+(head-old3['final_head_ps'])*5000/3334)*1e-12
        delta_decode=dec['elapsed_ps']*1e-12-original['windows']['decode']['elapsed_ps']*1e-12
        additive_d=old['windows']['decode']['duration_s']+delta_decode*5000/3334
        record=dict(model=m,name=case['name'],timing=dict(position_ratio_200_300=ratios,position_200_ps=pos200,head_ratio=headratio,head_200_ps=h200,decode_ratio=rd,
            alternative_additive_prefill_s=additive,alternative_additive_decode_s=additive_d,
            migration_sensitivity_percent={'prefill512':100*(additive/tp-1),'decode':100*(additive_d/td-1)},
            old_200_curve_loo_percent_not_sequence_error=old2['full_layer_loo_max_abs_percent']),windows={})
        for phase,tnew in [('prefill512',tp),('decode',td)]:
            latest=case[phase] if phase=='prefill512' else dec
            if phase=='prefill512':
                t=latest['duration_s'];n=512;comp={k:list(v) for k,v in latest['components_j'].items() if k!='ddr_devices'}
                cmd,bg=case['audit']['ddr_command_j'],case['audit']['ddr_background_j'];beats=case['audit']['read_dma_beats512']
                historical=energy200[m]['windows']['prefill512'];u=uniform[m]
                cmdratio=historical['audit']['ddr_command_j']/u['audit']['ddr_command_j']
                bgwratio=(historical['audit']['ddr_background_refresh_j']/historical['duration_s'])/(u['audit']['ddr_background_j']/u['prefill512']['duration_s'])
                freqphase='prefill'
            else:
                t=latest['elapsed_ps']*1e-12;n=1;comp={k:scaled(v['energy_nj_per_window'],1e-9) for k,v in latest['components'].items()}
                cmd,bg=ddr_parts(rawddr);beats=latest['validated_counts']['read_dma_beats_64b'];freqphase='decode'
                dr=old['windows']['decode']['ddr_reintegration'];cmdratio=dr['command_ratio'];bgwratio=dr['background_refresh_ratio']/rd
            eq(t*n/t,n);eq(cmd+bg,(latest['components_j']['ddr_devices'][0] if phase=='prefill512' else latest['ddr']['energy_nj_per_window'][0]*1e-9))
            converted={};rules={};fr=old['windows'][freqphase]
            for k,e in comp.items():
                if k in fr['resident_reintegration']:
                    leak=fr['resident_reintegration'][k]['leakage_fraction_300'];rat=[(1-x)*2/3+x for x in leak]
                    value=[e[i]*tnew/t*rat[i] for i in (0,1)];rule=dict(kind='residence',power_ratio=rat,leakage_fraction=leak)
                elif k in ('m_busy_increment','m_ordinary_projection_increment'):
                    j=0 if k=='m_busy_increment' else 1;ratio=fr['m_increment_energy_ratios'][j];value=scaled(e,ratio);rule=dict(kind='M_busy_response',energy_ratio=ratio)
                elif k=='arithmetic_idle_sensitivity':
                    eq(e[1]/t,ar300);value=[0.,ar200*tnew];rule=dict(kind='residence',power_ratio=[ar200/ar300]*2)
                elif k=='native_mother_core_actual_parameter_reference':
                    for i in (0,1):eq(e[i]/t,control['mother'][i]['w300'])
                    value=[v['w200']*tnew for v in control['mother']];rule=dict(kind='residence',power_ratio=[v['w200']/v['w300'] for v in control['mother']])
                elif k=='local_shell_dispatch_reference_4x':
                    p3=[sum(v[i]['w300'] for v in control['local'].values()) for i in (0,1)];p2=[sum(v[i]['w200'] for v in control['local'].values()) for i in (0,1)]
                    for i in (0,1):eq(e[i]/t,p3[i])
                    value=scaled(p2,tnew);rule=dict(kind='residence',power_ratio=[p2[i]/p3[i] for i in (0,1)])
                elif k=='mother_periphery_reference_increment':
                    for i in (0,1):eq(e[i]/t,pp[i]['total'])
                    value=[power200(x)*tnew for x in pp];rule=dict(kind='residence',power_ratio=[power200(x)/x['total'] for x in pp])
                else:value=list(e);rule=dict(kind='fixed_event_energy')
                converted[k]=value;rules[k]=rule
            dd2cmd=cmd*cmdratio;dd2bg=bg*bgwratio*tnew/t
            window=dict(tokens=n,read_beats_64b=beats,time_ratio=tnew/t,transfer_rules=rules,
                ddr=dict(command_300_j=cmd,background_300_j=bg,command_ratio=cmdratio,background_power_ratio=bgwratio,command_200_j=dd2cmd,background_200_j=dd2bg),frequencies={})
            for f,tt,c,dd in [(300,t,comp,cmd+bg),(200,tnew,converted,dd2cmd+dd2bg)]:
                before=sums(c);r=None
                if m in rmodels:
                    rr=rmodels[m]['windows'][phase];term=rmodels[m]['proxy_removed'];removed=c.pop(term)
                    key='falcon-wide' if m=='falcon' else m
                    cal=read(B+('/recurrent-300mhz/' if f==300 else '/recurrent-step1/')+key+'-calibration.json')
                    samples=[s for s in cal['windows'] if s['segment']['window']==rr['sample_phase']];assert len(samples)==4
                    if f==200:assert cal['gate_replay_pass'] and cal['clock_mhz']==200
                    group=[sum(s['increment_nj'] for s in samples if s['segment']['group']==g)*1e-9 for g in (0,1)]
                    idle=[s['power_w']['idle']['total'] for s in samples];calls=rr['calls_16channel']
                    c['recurrent_dynamic']=[calls*min(group),calls*max(group)];c['recurrent_idle']=[min(idle)*tt,max(idle)*tt]
                    c['recurrent_injection']=rr['retained_injection_proxy_j']
                    service=max(sum(s['window_ps'] for s in samples if s['segment']['group']==g) for g in (0,1))*1e-12*calls
                    assert service<tt
                    r=dict(removed_term=term,removed_energy_j=removed,calls_16channel=calls,calibration_mhz=f,per_service_increment_j=group,idle_w=[min(idle),max(idle)],service_time_s=service,full_model_deployment_accepted=False)
                chip=sums(c);scenarios={}
                for variant,co in dma_coefs.items():
                    dyn=scaled(co['dynamic_nj_per_64b'],beats*1e-9);idle=scaled(dma_powers[variant][str(f)],tt);add=[dyn[i]+idle[i] for i in (0,1)]
                    ce=[chip[i]+add[i] for i in (0,1)]
                    scenarios[variant]=dict(idle_j=idle,dynamic_j=dyn,dma_energy_j=add,scopes=dict(on_chip=metric(ce,tt,n),on_chip_plus_ddr=metric([v+dd for v in ce],tt,n)))
                env=[min(s['scopes']['on_chip']['energy_j_per_window'][0] for s in scenarios.values()),max(s['scopes']['on_chip']['energy_j_per_window'][1] for s in scenarios.values())]
                entry=dict(duration_s=tt,tokens_per_second=n/tt,components_j=c,ddr_j=dd,base_on_chip_j=chip,before_recurrent_on_chip_j=before,recurrent=r,dma_scenarios=scenarios,
                    scopes=dict(on_chip=metric(env,tt,n),on_chip_plus_ddr=metric([v+dd for v in env],tt,n)))
                if f==300:
                    target=rmodels[m]['windows'][phase]['dma_candidate_envelope'] if m in rmodels else None
                    if target:
                        for scope in target:
                            for i in (0,1):eq(entry['scopes'][scope]['energy_j_per_window'][i],target[scope]['energy_j_per_window'][i])
                window['frequencies'][str(f)]=entry
            record['windows'][phase]=window
        out.append(record)
        print(m,round(512/tp,6),round(1/td,6),flush=True)
    result=dict(version='SYNC-08 dual frequency v5 + narrowed recurrent',created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),source=source,
        sram_bits=512,p_lanes=3,core_period_ps={'300':3334,'200':5000},ddr_period_ps=630,nominal_dynamic_power_ratio=2/3,
        fixed_voltage_temperature=True,new_simulation_jobs=[],new_200_e32_18_replay=False,full_prefill512_measured=False,full_model_numeric_or_physical_accepted=False,
        method='legacy paired-frequency/context response transferred onto latest v5, component-resolved power; same mapped recurrent candidate calibrated at each frequency',
        models=out,dma_idle_transfer=dma_powers,input_sha256=SOURCES)
    dump(HERE/'results.json',result);dump(HERE/'input-manifest.json',{'files':SOURCES,'source_commits':source,'method_sources':['PR294 results-200mhz / prefill-v3 / power-v4','PR295 R200 + R300'],'no_original_inputs_modified':True})
if __name__=='__main__':main()
