"""Independently check energy units, component conservation and replacement."""
import json
from math import isclose,isfinite
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_bytes())
def eq(a,b):assert len(a)==len(b) and all(isclose(x,y,rel_tol=1e-11,abs_tol=1e-6) for x,y in zip(a,b)),(a,b)
def energy(x):return x['energy_nj_per_window']
def add(a,b):return [x+y for x,y in zip(a,b)]
def units(x,ps,tokens):
    e=energy(x);assert all(isfinite(v) and v>=0 for v in e) and e[0]<=e[1]
    eq(x['average_power_w'],[v*1000/ps for v in e])
    eq(x['energy_mj_per_token'],[v/1e6/tokens for v in e])

def main():
    total=0
    for p in sorted((HERE/'timing-ledger').glob('*.json')):
        if p.stem=='index':continue
        timing=load(p);dma=load(HERE/'dma-ledger'/p.name);special=load(HERE/'special-candidate-ledger'/p.name)
        assert timing['model']==dma['model']==special['model']
        for name,w in timing['windows'].items():
            total+=1;ps,tokens=w['elapsed_ps'],w['tokens']
            chip=[sum(energy(v)[e] for v in w['components'].values()) for e in (0,1)]
            eq(chip,energy(w['estimated_on_chip']))
            eq(add(chip,energy(w['ddr'])),energy(w['estimated_on_chip_plus_ddr']))
            for x in [*w['components'].values(),w['estimated_on_chip'],w['estimated_on_chip_plus_ddr'],w['ddr']]:units(x,ps,tokens)
            s=special['windows'][name];new=[v for k,v in w['components'].items() if k not in s['removed_proxies']]
            for k,v in s['removed_proxies'].items():eq(energy(v),energy(w['components'][k]))
            new+=list(s['replacement_components'].values())+[s['candidate_idle']]
            sch=[sum(energy(x)[e] for x in new) for e in (0,1)]
            eq(sch,energy(s['estimated_on_chip']))
            eq(add(sch,energy(w['ddr'])),energy(s['estimated_on_chip_plus_ddr']))
            for variant,entry in dma['scenarios'].items():
                d=entry['windows'][name];coef=entry['coefficient']
                assert d['read_beats_64b']==w['validated_counts']['read_dma_beats_64b']
                eq(energy(d['read_dma_dynamic']),[x*d['read_beats_64b'] for x in coef['dynamic_nj_per_64b']])
                eq(energy(d['read_dma_idle']),[x*ps/1000 for x in coef['idle_w']])
                de=add(energy(d['read_dma_idle']),energy(d['read_dma_dynamic']))
                eq(de,energy(d['read_dma_total']))
                eq(add(chip,de),energy(d['estimated_on_chip']))
                eq(add(add(chip,de),energy(w['ddr'])),energy(d['estimated_on_chip_plus_ddr']))
                candidate=s['dma_scenarios'][variant]
                eq(add(sch,de),energy(candidate['estimated_on_chip']))
                eq(add(add(sch,de),energy(w['ddr'])),energy(candidate['estimated_on_chip_plus_ddr']))
                for x in [d[k] for k in ('read_dma_idle','read_dma_dynamic','read_dma_total','estimated_on_chip','estimated_on_chip_plus_ddr')]+list(candidate.values()):units(x,ps,tokens)
            assert not special['physical_binding_accepted'] and not special['rtl_full_model_numeric_accepted']
    assert total>0
    receipt=dict(passed=True,windows=total,checks=['energy/W/mJ-per-token units','component conservation',
        'old proxy removed exactly once','single alternative DMA fabric per scenario','candidate coverage flags retained'])
    (HERE/'integrated-ledger-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('INTEGRATED_LEDGER_PASS',total)

if __name__=='__main__':main()
