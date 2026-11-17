"""Extend seven accepted TLM subtotals using no-wire component references.

This is an explicitly conditional, incomplete on-chip subtotal. It is not a
new physical implementation or a whole-chip measurement. Unbound arithmetic,
read DMA, controller shell, PHY and other uncovered work remain unknown.
"""
from collections import Counter
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import re
import sys
from six_model_tlm_power import metrics, pair, ordered_sum

HERE = Path(__file__).resolve().parent
MODELS = ('qwen3','llama','granite','phi','gemma','qwen35','falcon')
NEW_TERMS = ('m_ordinary_projection_increment','write_dma_clocked_idle_1x',
    'u_add_chain_clocked_idle_1x','pm_transport_clocked_idle_1x','pm_transport_install_increment',
    'lc_pm_boot_crc_increment','lc_pm_runtime_read_increment','lc_descriptor_fetch_active_increment',
    'native_mother_core_reference_1x')


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def bounds(values):
    values=list(values)
    if not values or min(values)<0:
        raise ValueError('missing or negative coefficient')
    return [min(values),max(values)]


def scale(values, n):
    return [x*n for x in pair(values)]


def difference(active, quiet):
    if any(active['timing'].get(k) != quiet['timing'].get(k)
           for k in ('window_ps','clock_hz','source_period_ps','clock_edges')):
        raise ValueError('unpaired calibration window')
    return (active['power_w']['total']-quiet['power_w']['total'])*active['timing']['window_ps']/1000


def coefficients():
    root=HERE/'no-wire-results'
    data={name:load(root/(name+'.json')) for name in ('m','control','write_u','sram','legacy','mother-pm')}
    for name, obj in data.items():
        if obj.get('wire_parasitics_loaded') is not False:
            raise ValueError('reference includes wire parasitics: '+name)
        if name!='mother-pm':
            for case in obj['windows'].values():
                if case['wire_parasitics_loaded'] or case['timing']['clock_hz']!=300000000:
                    raise ValueError('inconsistent no-wire case')
            manifest=(root/(name+'-results.sha256')).read_text()
            if digest(root/(name+'.json'))+'  calibration.json' not in manifest:
                raise ValueError('server calibration manifest mismatch: '+name)
    if digest(root/'mother-pm.json')+'  mother-pm/mother-pm-macro-power.json' not in (root/'legacy-results.sha256').read_text():
        raise ValueError('server macro manifest mismatch')
    m=data['m']['windows']
    idle=next(x['power_w']['total'] for k,x in m.items() if 'idle-' in k)
    inc=bounds(x['power_w']['total']-idle for k,x in m.items() if '__m-38809662__' in k)
    c={'m_idle_w':idle,'m_increment_w':inc}
    s={k.split('__')[-1]:v for k,v in data['sram']['windows'].items()}
    counts={'read128':64,'write128':16,'write256':16,'write512':16,'read512':16}
    c['sram_idle_w']=s['idle']['power_w']['total']
    c['sram_access_nj']={k:difference(s[k],s['idle'])/n for k,n in counts.items()}
    for x in c['sram_access_nj'].values():bounds([x])
    lc=data['control']['windows']
    pmq={k.split('__')[-2]:v for k,v in lc.items() if k.startswith('pm-quiet__')}
    pma={k.split('__')[-2]:v for k,v in lc.items() if k.startswith('pm-runtime__')}
    requests=load(HERE/'qwen3_c639_pm_quiet_pair.json')['windows']
    c['lc_pm_idle_w_per_site']=bounds(x['power_w']['total'] for x in pmq.values())
    c['lc_pm_read_nj']=bounds(difference(pma[k],pmq[k])/requests[k]['requests'] for k in pmq)
    boot={k.split('__')[-1]:v for k,v in lc.items() if k.startswith('pm-arrays__')}
    c['lc_pm_boot_nj']=difference(boot['boot1'],boot['boot2'])
    fetch={k.split('__')[-2]:v for k,v in lc.items() if k.startswith('lc-fetch-')}
    fcounts=load(HERE/'qwen3_lc_fetch_power.json')['windows']
    c['fetch_idle_w_by_site']=[]
    for site in range(4):
        c['fetch_idle_w_by_site'].append(bounds(v['power_w']['total'] for k,v in fetch.items()
            if k.endswith('-site'+str(site)) and not any(fcounts[k]['transactions'].values())))
    fetch_cost=[]
    for mode in range(2):
        for site in range(3):
            key='mode-{}-writer-active-site{}'.format(mode,site)
            count=fcounts[key]['transactions']
            if count['start']!=1 or count['mc_req']!=2 or count['mc_rsp']!=2:
                raise ValueError('unexpected descriptor sample')
            quiet=fetch['mode-{}-down-site{}'.format(mode,site)]
            fetch_cost.append(difference(fetch[key],quiet))
    c['fetch_descriptor_nj']=bounds(fetch_cost)
    u=data['write_u']['windows']
    terms={k:v for k,v in u.items() if k.startswith('u-component')}
    c['u_idle_w']=sum(v['power_w']['total'] for k,v in terms.items() if k.endswith('__quiet'))
    c['u_add_nj_per_word']=sum(difference(v,terms[k.rsplit('__',1)[0]+'__quiet'])/32
                              for k,v in terms.items() if k.endswith('__active'))
    writes={k.split('__')[-2]:v for k,v in u.items() if k.startswith('real-span')}
    c['write_idle_w']=bounds(v['power_w']['total'] for k,v in writes.items() if k.endswith('-1'))
    c['write_nj_per_64b']=bounds(difference(v,writes[k[:-1]+'1'])/8
                               for k,v in writes.items() if k.endswith('-0'))
    pm={k.split('__')[-2]:v for k,v in u.items() if k.startswith('pm-real-length')}
    c['pm_transport_idle_w']=bounds(v['power_w']['total'] for k,v in pm.items() if k.endswith('-1'))
    c['pm_transport_page_nj']={}
    for kind in ('local-352','mother-240','mother-272','mother-1616'):
        c['pm_transport_page_nj'][kind]=bounds(difference(pm[kind+'-'+str(mode)+'-0'],pm[kind+'-'+str(mode)+'-1']) for mode in range(2))
    c['pm_transport_nj_per_word']=bounds(v/(int(k.split('-')[1])//16)
        for k,values in c['pm_transport_page_nj'].items() if k.startswith('mother-') for v in values)
    macro=data['mother-pm']
    c['mother_pm_idle_w']=macro['pages'][0]['cases']['read-quiet']['opensta_w']['total']
    c['mother_pm_install_nj']={}
    for p in macro['pages']:
        cost=sum(p['increment'][kind]['exact_clock_arc_pj'] for kind in ('read','write'))/1000
        cost+=p['increment']['write']['duration_s']*1e9*(p['cases']['write-quiet']['opensta_w']['total']-p['cases']['read-quiet']['opensta_w']['total'])
        c['mother_pm_install_nj'][p['bytes']]=cost
    c['mother_pm_install_nj_per_word']=bounds(v/(n//16) for n,v in c['mother_pm_install_nj'].items())
    old={k.split('__')[-1]:v for k,v in data['legacy']['windows'].items()}
    c['g32_idle_w']=bounds(v['power_w']['total'] for k,v in old.items() if k.startswith('g32') and k.endswith('-down'))
    c['g32_32word_call_nj']=bounds(difference(old['g32-mode-'+str(mode)+'-g32-active'],old['g32-mode-'+str(mode)+'-down']) for mode in (0,1))
    c['switch_idle_w']=bounds(v['power_w']['total'] for k,v in old.items() if k.startswith('switch'))
    native=root/'native-mother.json'
    c['native_mother_w']=None
    if native.exists():
        mother=load(native)
        if (mother['targets'],mother['STALL_LIMIT'],mother['SERVICE_STALL_LIMIT'],mother['clock_mhz'],mother['wire_parasitics_loaded'])!=(9,4096,4096,300,False):
            raise ValueError('wrong native mother configuration')
        c['native_mother_w']=bounds(v['power_w']['total'] for v in mother['windows'].values())
    c['input_sha256']={str(p.relative_to(HERE)):digest(p) for p in root.glob('*.json') if p.name not in ('coefficients.json',)}
    for name in ('qwen3_c639_pm_quiet_pair.json','qwen3_lc_fetch_power.json'):
        c['input_sha256'][name]=digest(HERE/name)
    return c


def stage_data(model):
    directory=HERE/('qwen3-ordinary-results' if model=='qwen3' else 'six-model-results/'+model)
    data={mode:{name:load(directory/mode/(name+'.json')) for name in ('result','component-observation')}
          for mode in ('prefill','decode')}
    hashes={str(p.relative_to(HERE)):digest(p) for mode in data for p in (directory/mode).glob('*.json')}
    if model=='qwen3':
        accepted=load(directory/'acceptance.json')
        if not all(x['complete_result_equal'] and x['numerical_files_equal'] and x['ordinary_and_ffn_intervals_disjoint'] for x in accepted.values()):
            raise ValueError('Qwen3 observation was not accepted')
        hashes[str((directory/'acceptance.json').relative_to(HERE))]=digest(directory/'acceptance.json')
    else:
        for mode in data:
            a=load(directory/mode/'acceptance.json')
            if not all(a.get(k) is True for k in ('passed','complete_result_equal','numerical_files_equal','ddr_terminal_reconciled','sram_observer_reconciled')):
                raise ValueError('model replay was not accepted')
    return data, hashes


def integrate(model, c):
    prior=load(HERE/(model+'_tlm_power_v1.json'))
    stages, hashes=stage_data(model)
    missing=[
        'Read DMA mapped-cell idle/leakage and measured read activity; write-price proxy is sensitivity only.',
        'Mother PM runtime instruction fetch and controller boot/deployment activity outside sampled C639 states.',
        'Local controller shell, dispatch, switch active traffic and other unbound control; only named leaves are included.',
        'RMS/normalization, softmax, rotary, extra scaling and unbound arithmetic; GELU, sigmoid, router, GDN/Mamba2 as applicable.',
        'DDR PHY and board I/O; these are not contained in the DDR device model.',
        'Unsynthesized global clock buffers/clock generation and unbound cross-block interconnect cells. Wire RC is excluded by choice.',
    ]
    if c['native_mother_w'] is None:missing.append('Nine-target mother core: no accepted synthesis power result yet.')
    assumptions=[
        'No wire SPEF or estimated wire RC is loaded. Existing mapped networks retain their actual buffers and pin capacitances; only the native mother core is newly synthesized.',
        'Keep accepted TLM windows (3334 ps core step, nominal 300 MHz). Component powers use 300 MHz and do not establish timing closure.',
        'Conditional shared footprint: 3 M, 4 S_P, 4 LC PM/fetch, one G32, switch, write scope, U ADD chain and PM transport bridge, and 4 mother PM macros. Actual per-model deployment is not proven.',
        'Both FFN and ordinary projection M intervals use the same sampled C639 active-minus-idle coefficient. Ordinary arithmetic modes and model bit-pattern transfer remain unqualified.',
        'LC PM runtime uses 23 reads per successful top-level service (20 metadata plus 3 instruction requests), applied to accepted per-position service counts. Nested arithmetic within a service does not create an extra LC call.',
        'One 128-byte descriptor fetch per top-level service. Apply C639 start/two-response incremental samples and paired LC PM samples to each model count.',
        'Local PM boot adds the existing empty-baseline paired boot/CRC increment once per observed install. Program-state differences from the loaded idle reference remain a transfer limitation.',
        'Unknown mother-page sizes scale measured per-word costs. Missing 256/384-bit read and 384-bit write coefficients use serial 128-bit operations at fixed TLM time.',
        'Newly counted resident write/U/PM-bridge networks are single shared instances in this reference; topology or gating changes require updating these multiplicities.',
        'Native mother, when available, uses the range of six C639 mapped boundary-activity powers for the whole window. This is a sampled-state transfer, not a measured full-model duty cycle.',
        'All ranges are sampled coefficient endpoints, not uncertainty bounds; uncalibrated components are not zero.',
    ]
    result={'model':prior['model'],'target_clock_mhz':300,'sram_scenario':'s_p_parallel_read',
        'scope':'Extended partial on-chip and on-chip plus DDR estimates without wire parasitics',
        'coverage_complete':False,'wire_parasitics_loaded':False,'assumptions':assumptions,
        'not_included':missing,'m_timing_wns_ns':prior['m_timing_wns_ns'],
        'input_sha256':dict(c['input_sha256'],**hashes),'windows':{}}
    result['input_sha256'][model+'_tlm_power_v1.json']=digest(HERE/(model+'_tlm_power_v1.json'))
    for name, original in prior['windows'].items():
        stage=stages['prefill' if name=='prefill' else 'decode']
        obs=stage['component-observation']['windows'][name]
        ps,tokens=original['elapsed_ps'],original['tokens']
        if ps!=obs['boundaries']['end_ps']-obs['boundaries']['start_ps']:raise ValueError('window mismatch')
        busy=[s.get('busy_interval_union_ps',0) for s in obs['modeled_m_by_site']]
        ordinary=[s.get('busy_interval_union_ps',0) for s in obs['ordinary_projection_m_by_site']]
        if any(a+b>ps for a,b in zip(busy,ordinary)) or busy[3] or ordinary[3]:
            raise ValueError('M capacity or site mismatch')
        if model=='qwen3':
            count=2 if name=='prefill' else 1
            pages=Counter({240:count,1616:28*count})
            if name!='prefill':pages[272]+=1
            activations={'silu':count*28*24}
            add_words=count*28*2*256
        else:
            events=obs['model_events'];pages=Counter();activations=Counter()
            for key,n in events.items():
                p=re.fullmatch(r'pm_mother_bytes_(\d+)',key)
                if p:pages[int(p[1])]+=n
                a=re.fullmatch(r'activation_(.+)_site\d+_words(\d+)',key)
                if a:activations[a[1]]+=n*int(a[2])/32
            add_words=sum(n for k,n in events.items() if re.fullmatch(r'leaf_\d+_e_add_packets_cycles9',k))
        if sum(pages.values())!=obs['pm']['mother']['images'] or sum(n*b for b,n in pages.items())!=obs['pm']['mother']['bytes']:
            raise ValueError('mother page accounting mismatch')
        local=obs['pm']['local'].get('images',0)
        if obs['pm']['local'].get('bytes',0)!=local*352:raise ValueError('unexpected local PM image')
        calls=[0]*4
        for row in stage['result']['services']:
            group=row['group']
            selected=name=='prefill' or group.startswith('pos512-' if name=='first_token' else 'pos513-')
            if selected:calls[row['signature'][0]]+=row['count']
        if sum(row['count'] for row in stage['result']['services'])!=sum(row['count'] for row in stage['result']['calls']):
            raise ValueError('service aggregate mismatch')
        energy={k:original['components'][k]['energy_nj_per_window'] for k in ('ddr_devices',)}
        def resident(key, watts, count=1):energy[key]=scale(watts,ps*count/1000)
        resident('m_clocked_idle_3x',c['m_idle_w'],3)
        energy['m_busy_increment']=scale(c['m_increment_w'],sum(busy)/1000)
        energy['m_ordinary_projection_increment']=scale(c['m_increment_w'],sum(ordinary)/1000)
        resident('s_p_clocked_idle_4x',c['sram_idle_w'],4)
        sram=0
        for site in obs['sram_by_site']:
            for op in ('read','write'):
                ns={bits:site.get(op+'_'+str(bits)+'bit',0) for bits in (128,256,384,512)}
                if sum(ns.values())!=site.get(op+'_beats',0) or sum(n*bits//8 for bits,n in ns.items())!=site.get(op+'_bytes',0):
                    raise ValueError('SRAM width accounting mismatch')
                for bits,n in ns.items():
                    cost=c['sram_access_nj'].get(op+str(bits),c['sram_access_nj'][op+'128']*(bits//128))
                    sram+=n*cost
        energy['s_p_access_increment']=pair(sram)
        resident('mother_pm_clocked_idle_4_macros',c['mother_pm_idle_w'])
        install=[0.,0.];bridge=scale(c['pm_transport_page_nj']['local-352'],local)
        for size,n in pages.items():
            macro=pair(c['mother_pm_install_nj'][size]) if size in c['mother_pm_install_nj'] else scale(c['mother_pm_install_nj_per_word'],size//16)
            trans=c['pm_transport_page_nj'].get('mother-'+str(size),scale(c['pm_transport_nj_per_word'],size//16))
            install=[a+n*b for a,b in zip(install,macro)]
            bridge=[a+n*b for a,b in zip(bridge,trans)]
        energy['mother_pm_page_install_and_readback_increment']=install
        resident('lc_pm_loaded_quiet_4x',c['lc_pm_idle_w_per_site'],4)
        energy['lc_pm_boot_crc_increment']=scale(c['lc_pm_boot_nj'],local)
        energy['lc_pm_runtime_read_increment']=scale(c['lc_pm_read_nj'],23*sum(calls))
        fetch_idle=[sum(x[edge] for x in c['fetch_idle_w_by_site']) for edge in (0,1)]
        resident('lc_descriptor_fetch_quiet_4x',fetch_idle)
        energy['lc_descriptor_fetch_active_increment']=scale(c['fetch_descriptor_nj'],sum(calls))
        resident('g32_down_idle_1x',c['g32_idle_w'])
        energy['g32_active_increment']=scale(c['g32_32word_call_nj'],activations.get('silu',0)+activations.get('scaled_silu',0))
        resident('cohort_switch_idle_1x',c['switch_idle_w'])
        energy['u_add2_logic_active_increment']=scale(c['u_add_nj_per_word'],add_words)
        resident('u_add_chain_clocked_idle_1x',c['u_idle_w'])
        resident('write_dma_clocked_idle_1x',c['write_idle_w'])
        beats=original['ddr_transport_beats_64b']
        energy['write_dma_active_increment']=scale(c['write_nj_per_64b'],beats['write'])
        resident('pm_transport_clocked_idle_1x',c['pm_transport_idle_w'])
        energy['pm_transport_install_increment']=bridge
        if c['native_mother_w'] is not None:resident('native_mother_core_reference_1x',c['native_mother_w'])
        total=[ordered_sum(v[e] for v in energy.values()) for e in (0,1)]
        chip=[v-energy['ddr_devices'][e] for e,v in enumerate(total)]
        added=[sum(energy[k][e] for k in NEW_TERMS if k in energy) for e in (0,1)]
        sensitivities={}
        for label,factor in (('half_write_cost',.5),('same_write_cost',1),('twice_write_cost',2)):
            assumed=sum(c['write_nj_per_64b'])/2*factor
            proxy=assumed*beats['read']
            sensitivities[label]={'assumed_read_pj_per_64b':assumed*1000,
                'read_dma_active_proxy':metrics(proxy,ps,tokens),
                'subtotal_with_read_dma_active_proxy':metrics([x+proxy for x in total],ps,tokens)}
        result['windows'][name]={'elapsed_ps':ps,'tokens':tokens,'tokens_per_second':original['tokens_per_second'],
            'token_kind':original['token_kind'],'ddr_transport_beats_64b':beats,
            'm_ffn_busy_ps_by_site':busy,'m_ordinary_busy_ps_by_site':ordinary,
            'top_level_service_calls_by_site':calls,'local_pm_runtime_reads':23*sum(calls),
            'local_pm_installs':local,'mother_page_counts':dict(pages),
            'components':{k:metrics(v,ps,tokens) for k,v in energy.items()},
            'newly_included_components':{k:metrics(energy[k],ps,tokens) for k in NEW_TERMS if k in energy},
            'newly_included_subtotal':metrics(added,ps,tokens),
            'covered_on_chip_subtotal':metrics(chip,ps,tokens),'covered_subtotal':metrics(total,ps,tokens),
            'prior_with_wire_covered_on_chip_subtotal':original['covered_on_chip_subtotal'],
            'prior_with_wire_covered_subtotal':original['covered_subtotal'],
            'same_old_components_without_wire':metrics([v-added[e] for e,v in enumerate(total)],ps,tokens),
            'read_dma_dynamic_sensitivity':sensitivities,'write_dma_transferred_pj_per_64b':scale(c['write_nj_per_64b'],1000),
            'read_dma_idle_w':None,'remaining_100mw_residency_mj_per_token':.1*ps/1e9/tokens}
        for e in (0,1):
            assert isclose(chip[e]+energy['ddr_devices'][e],total[e],rel_tol=1e-12)
    return result


def main():
    c=coefficients()
    (HERE/'no-wire-results/coefficients.json').write_bytes((json.dumps(c,indent=2)+'\n').encode())
    for model in sys.argv[1:] or MODELS:
        result=integrate(model,c)
        path=HERE/(model+'_tlm_power_v2_no_wire.json')
        path.write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())
        print(model, json.dumps({w:{k:r[k]['energy_mj_per_token'] for k in ('covered_on_chip_subtotal','covered_subtotal','newly_included_subtotal')} for w,r in result['windows'].items()}))


if __name__=='__main__':main()
