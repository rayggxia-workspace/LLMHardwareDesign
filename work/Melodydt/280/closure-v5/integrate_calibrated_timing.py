"""Reintegrate accepted E32-18 windows without scaling count-based energy.

This preserves the explicitly conditional v4 footprint and arithmetic
scenarios. It is a partial v5 ledger, not completed physical deployment.
"""
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
from six_model_tlm_power import metrics

RESIDENT={
    'm_clocked_idle_3x','s_p_clocked_idle_4x','mother_pm_clocked_idle_4_macros',
    'lc_pm_loaded_quiet_4x','lc_descriptor_fetch_quiet_4x','g32_down_idle_1x',
    'cohort_switch_idle_1x','u_add_chain_clocked_idle_1x',
    'write_dma_clocked_idle_1x','pm_transport_clocked_idle_1x'}
MTERMS={'m_busy_increment':'modeled_m_by_site',
        'm_ordinary_projection_increment':'ordinary_projection_m_by_site'}

def load(p):return json.loads(p.read_text())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def energy(row):return row['energy_nj_per_window']
def sum_energy(rows):return [sum(energy(v)[e] for v in rows.values()) for e in (0,1)]
def normalized_events(rows):return {k.replace('e_product_packets_cycles18','e_product_packets_cycles9'):v for k,v in rows.items()}
def pm_counts(rows):return {k:{a:b for a,b in v.items() if a!='elapsed_including_ddr_wait_ps'} for k,v in rows.items()}


def main():
    out=HERE/'timing-ledger';out.mkdir(exist_ok=True)
    periphery=load(HERE/'control-periphery-calibration.json')
    pvalues=[x['power_w']['total'] for x in periphery['windows'].values()]
    assert len(periphery['cut_instances'])==10 and periphery['wire_parasitics_loaded'] is False
    index=[]
    for folder in sorted((HERE/'deployments').glob('*-e32-18')):
        model,phase=folder.name.split('-')[:2]
        base=folder.with_name(model+'-'+phase+'-observe')/'result';stage=folder/'result'
        a,b=[load(p/'acceptance.json') for p in (base,stage)]
        assert a['passed'] and a['complete_result_equal'] and b['passed'] and b['numerical_and_traffic_invariants_equal']
        assert b['numerical_files_equal'] and b['ddr_terminal_reconciled']
        old,new=[load(p/'component-observation.json')['windows'] for p in (base,stage)]
        bo,do=[load(p/'deployment-observation.json') for p in (base,stage)]
        assert do['calibrated_e32_product_cycles']==18 and do['core_period_ps']==3334 and do['data_sram_bits']==512
        assert bo['bindings']==do['bindings']
        dma=load(stage/'dma-windows.json');ddr=load(stage/'ddr-window-energy.json')['windows']
        v2=load(PARENT/(model+'_tlm_power_v2_no_wire.json'))
        v4=load(PARENT/(model+'_tlm_power_v4_control.json'))
        windows={}
        for name,d in ddr.items():
            prior=v4['windows'][name];prior2=v2['windows'][name];o,n=old[name],new[name]
            ps,tokens=d['elapsed_ps'],d['tokens'];oldps=prior['elapsed_ps']
            assert oldps==bo['windows'][name]['elapsed_ps'] and ps==do['windows'][name]['elapsed_ps']
            assert tokens==prior['tokens']
            assert o['sram_by_site']==n['sram_by_site']
            assert normalized_events(o['model_events'])==normalized_events(n['model_events'])
            assert pm_counts(o['pm'])==pm_counts(n['pm'])
            for key in MTERMS.values():
                assert [r.get('groups_dispatched',0) for r in o[key]]==[r.get('groups_dispatched',0) for r in n[key]]
            routes=do['windows'][name]['routes']
            assert routes==bo['windows'][name]['routes']
            calls=[sum(v for k,v in routes.items() if k.startswith(str(site)+'/')) for site in range(4)]
            assert calls==prior2['top_level_service_calls_by_site']
            instructions=sum(v for k,v in do['windows'][name]['counters'].items() if k.startswith('mother_opcode_'))
            assert instructions==prior['control_counts']['instructions']
            beats={}
            for kind in ('read','write'):
                counts=[sum(c[kind][event] for c in dma[name]['channels']) for event in ('submitted','accepted','completed')]
                assert len(set(counts))==1
                beats[kind]=counts[0]
            assert beats==prior2['ddr_transport_beats_64b']
            components={};integration={}
            for key,row in prior2['components'].items():
                if key in ('ddr_devices','native_mother_core_reference_1x'):continue
                ratio=1.;rule='unchanged count, validated by accepted replay and per-window SRAM/PM/service/DDR checks'
                if key in RESIDENT:ratio=ps/oldps;rule='same conditional clocked footprint, actual corrected elapsed time'
                elif key in MTERMS:
                    oldbusy=sum(x.get('busy_interval_union_ps',0) for x in o[MTERMS[key]])
                    newbusy=sum(x.get('busy_interval_union_ps',0) for x in n[MTERMS[key]])
                    assert oldbusy or newbusy==0
                    ratio=newbusy/oldbusy if oldbusy else 1.
                    rule='actual corrected busy-interval union for the same shared M instances'
                components[key]=metrics([x*ratio for x in energy(row)],ps,tokens);integration[key]=rule
            for key,row in prior['arithmetic_components'].items():
                ratio=ps/oldps if key=='arithmetic_idle_sensitivity' else 1.
                components[key]=metrics([x*ratio for x in energy(row)],ps,tokens)
                integration[key]='same prior arithmetic scenario; elapsed time updated only for idle sensitivity'
            for key,row in prior['control_components'].items():
                ratio=ps/oldps if key in ('native_mother_core_actual_parameter_reference','local_shell_dispatch_reference_4x') else 1.
                components[key]=metrics([x*ratio for x in energy(row)],ps,tokens)
                integration[key]='same reference topology; actual elapsed time or validated instruction/flit counts'
            # Independently reconstruct v4 before adding new terms.
            oldparts={k:v for k,v in prior2['components'].items() if k not in ('ddr_devices','native_mother_core_reference_1x')}
            oldparts.update(prior['arithmetic_components']);oldparts.update(prior['control_components'])
            assert all(isclose(x,y,rel_tol=1e-12) for x,y in zip(sum_energy(oldparts),energy(prior['estimated_on_chip'])))
            components['mother_periphery_reference_increment']=metrics([min(pvalues)*ps/1000,max(pvalues)*ps/1000],ps,tokens)
            integration['mother_periphery_reference_increment']='C639 peripheral cut excludes the already counted core, four LC, four routers and switch; state range transfer, not exact model RTL state mix'
            chip=sum_energy(components);device=d['device_j']*1e9
            windows[name]=dict(elapsed_ps=ps,tokens=tokens,tokens_per_second=d['tok_s'],components=components,
                integration_rules=integration,estimated_on_chip=metrics(chip,ps,tokens),
                ddr=metrics([device,device],ps,tokens),
                estimated_on_chip_plus_ddr=metrics([x+device for x in chip],ps,tokens),
                validated_counts=dict(read_dma_beats_64b=beats['read'],write_dma_beats_64b=beats['write'],
                                      local_calls_by_site=calls,mother_instructions=instructions),
                no_unproven_gating_savings_added=True)
        result=dict(model=model,phase=phase,scope='E32 timing-corrected conditional subtotal plus C639 mother periphery reference; DMA/special pin calibration not yet integrated',
            target_clock_mhz=300,sram_bits=512,wire_parasitics_loaded=False,coverage_complete=False,
            physical_model_binding_accepted=False,m_timing_closure_required=False,windows=windows,
            inputs={str(p.relative_to(PARENT)):digest(p) for p in [stage/'acceptance.json',stage/'deployment-observation.json',stage/'component-observation.json',
              stage/'ddr-window-energy.json',PARENT/(model+'_tlm_power_v4_control.json'),HERE/'control-periphery-calibration.json']},
            not_included=['matched read-DMA paired pin calibration and per-model integration',
              'full physical model top/provider adapters, actual model router configuration and clock-gating implementation',
              'exact complete-model RTL control-state residence; current exact intervals are TLM only',
              'new special-operator candidate integration and FP32 conversion/provider wrappers',
              'DDR PHY/package/board I/O and global clock/physical interconnect; wire parasitics intentionally excluded'])
        dest=out/(model+'-'+phase+'.json');dest.write_text(json.dumps(result,indent=2)+'\n')
        index.append(dict(model=model,phase=phase,sha256=digest(dest),windows=list(windows)))
    (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    print('TIMING_LEDGER_PASS',len(index))


if __name__=='__main__':main()
