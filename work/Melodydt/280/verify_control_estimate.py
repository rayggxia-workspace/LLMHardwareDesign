"""Independent conservation, units, frozen-input and control-boundary checks."""
import hashlib
import json
from math import isclose
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MODELS=('qwen3','llama','granite','phi','gemma','qwen35','falcon')
def read(p):return json.loads(p.read_bytes())
def close(a,b):
    if not isclose(a,b,rel_tol=2e-12,abs_tol=1e-6):raise ValueError((a,b))


def main():
    count=read(ROOT/'control-gap-results/model-control-counts.json')
    local=read(ROOT/'control-gap-results/local.json')
    assert len(local['instances'])==8
    for instance in local['instances'].values():
        assert len(instance['windows'])==6
        for w in instance['windows'].values():assert w['annotated']==w['port_bits']
    windows=0
    for m in MODELS:
        new=read(ROOT/(m+'_tlm_power_v4_control.json'))
        old=read(ROOT/(m+'_tlm_power_v3_arithmetic.json'))
        base=read(ROOT/(m+'_tlm_power_v2_no_wire.json'))
        assert new['sram_bits']==512 and new['target_clock_mhz']==300 and not new['wire_parasitics_loaded']
        assert hashlib.sha256((ROOT/(m+'_tlm_power_v3_arithmetic.json')).read_bytes()).hexdigest()==new['previous_v3_sha256']
        for name,h in new['control_input_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
        for name,w in new['windows'].items():
            prev=old['windows'][name];b=base['windows'][name];c=count['models'][m][name]
            for k in ('elapsed_ps','tokens','tokens_per_second','ddr','arithmetic_components','arithmetic_increment','operation_audit'):assert w[k]==prev[k]
            assert w['control_counts']['instructions']==sum(p['instructions'] for p in c['pages'])
            assert c['calls_by_site']==[sum(p['calls_by_site'][i] for p in c['pages']) for i in range(4)]
            assert c['control_packet_flits']==8*sum(c['calls_by_site'])
            removed=b['components']['native_mother_core_reference_1x']['energy_nj_per_window']
            for e in (0,1):
                added=sum(v['energy_nj_per_window'][e] for v in w['control_components'].values())
                delta=added-removed[e]
                close(delta,w['control_net_increment']['energy_nj_per_window'][e])
                close(prev['estimated_on_chip']['energy_nj_per_window'][e]+delta,w['estimated_on_chip']['energy_nj_per_window'][e])
                close(w['estimated_on_chip']['energy_nj_per_window'][e]+w['ddr']['energy_nj_per_window'][e],w['estimated_on_chip_plus_ddr']['energy_nj_per_window'][e])
            groups=list(w['control_components'].values())+[w['estimated_on_chip'],w['estimated_on_chip_plus_ddr'],w['control_net_increment']]
            for v in groups:
                assert 0<=v['energy_nj_per_window'][0]<=v['energy_nj_per_window'][1]
                for e in (0,1):
                    n=v['energy_nj_per_window'][e]
                    close(n*1000/w['elapsed_ps'],v['average_power_w'][e])
                    close(n/1e6/w['tokens'],v['energy_mj_per_token'][e])
            for label,s in w['read_dma_sensitivity'].items():
                assert s['read_dma_active_proxy']==prev['read_dma_sensitivity'][label]['read_dma_active_proxy']
                for k in ('estimated_on_chip','estimated_on_chip_plus_ddr'):
                    for e in (0,1):close(s[k]['energy_nj_per_window'][e],w[k]['energy_nj_per_window'][e]+s['read_dma_active_proxy']['energy_nj_per_window'][e])
            windows+=1
    print('CONTROL_ESTIMATE_PASS',windows,'windows; 48 LC annotations; all SHA/units/conservation/frozen DDR/arithmetics checked')


if __name__=='__main__':main()
