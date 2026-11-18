"""Add one synthesized read fabric per scenario to accepted timing ledgers.

The four variants are alternatives, never additive. Read traffic is a
conditional transfer until each model has a fully bound physical topology.
"""
import json
from pathlib import Path
from hashlib import sha256
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from six_model_tlm_power import metrics

def load(p):return json.loads(p.read_text())
def digest(p):return sha256(p.read_bytes()).hexdigest()

def main():
    coefficients={}
    boundary=load(HERE/'dma-shared-boundary.json')
    for path in sorted(HERE.glob('dma-*-pin-calibration.json')):
        data=load(path);variant=data['variant']
        assert digest(path)+'  calibration.json' in path.with_name('dma-'+variant+'-pin-results.sha256').read_text()
        assert data['clock_mhz']==300 and not data['wire_parasitics_loaded']
        assert 'reset fence completed' in data['operational_idle']
        idle=[row['power_w']['total'] for name,row in data['windows'].items() if name.startswith('idle-')]
        energies=[];samples=[];pin_set=None
        for name,row in data['windows'].items():
            pin=row['activity_pin_mapping']
            assert row['annotated']==pin['expected_annotated_pins']
            if pin_set is None:pin_set=pin['observed_pin_set_sha256']
            assert pin_set==pin['observed_pin_set_sha256']
        for mode in (0,1):
            active=data['windows']['active-'+str(mode)];quiet=data['windows']['idle-'+str(mode)]
            timing=boundary['windows']['mode-%d-gate-up'%mode]['timing']
            assert active['activity']['window_ps']==timing['window_ps']
            # Phase and shared are alternative wrappers around the same
            # accepted C639 active transaction stream, at owner 0.
            other=HERE/'dma-shared-pin-calibration.json'
            if other.exists():
                shared=load(other)['windows']['active-'+str(mode)]
                assert active['activity']['source_sha256']==shared['activity']['source_sha256']
            counts=timing['pre_edge_handshakes']
            ns=[counts[k] for k in ('c_req_valid','c_rsp_valid','d_req_valid','d_rsp_valid')]
            assert min(ns)>0
            # Window cuts differ in accepted/forwarded population; include
            # up to one initially unobserved edge (12 registered clients).
            denominator=[min(ns),max(ns)+12]
            delta=(active['power_w']['total']-quiet['power_w']['total'])*timing['window_ps']/1000
            assert delta>=0
            pair=[delta/denominator[1],delta/denominator[0]];energies+=pair
            samples.append(dict(mode=mode,active_minus_idle_nj=delta,observed_handshakes=counts,
                                coefficient_denominator=denominator,incremental_nj_per_64b=pair))
        coefficients[variant]=dict(idle_w=[min(idle),max(idle)],dynamic_nj_per_64b=[min(energies),max(energies)],
            samples=samples,calibration_sha256=digest(path),topology_binding='conditional single fabric instance',
            active_phase_owner='owner 0 only; owner 1 dynamic activity remains a transfer assumption' if variant.startswith('phase') else 'not applicable',
            annotation_scope='observed RTL bits mapped to connected cell pins; remaining internal activity is propagated, not complete gate-level replay',
            uncertainty='sample and window-population sensitivity, not confidence interval or guaranteed error bound',
            phase_shared_relation='phase contains shared; do not add these scenarios')
    (HERE/'dma-coefficients.json').write_text(json.dumps(coefficients,indent=2)+'\n')
    out=HERE/'dma-ledger';out.mkdir(exist_ok=True);index=[]
    for path in sorted((HERE/'timing-ledger').glob('*.json')):
        if path.stem=='index':continue
        base=load(path);result=dict(model=base['model'],phase=base['phase'],baseline_sha256=digest(path),
            scope='conditional synthesized-read-DMA alternatives added to E32-corrected partial subtotal',
            physical_binding_accepted=False,wire_parasitics_loaded=False,scenarios={})
        for variant,c in coefficients.items():
            windows={}
            for name,w in base['windows'].items():
                ps,tokens=w['elapsed_ps'],w['tokens'];reads=w['validated_counts']['read_dma_beats_64b']
                idle=[x*ps/1000 for x in c['idle_w']];dynamic=[x*reads for x in c['dynamic_nj_per_64b']]
                total=[x+y for x,y in zip(idle,dynamic)]
                windows[name]=dict(elapsed_ps=ps,tokens=tokens,read_beats_64b=reads,
                    read_dma_idle=metrics(idle,ps,tokens),read_dma_dynamic=metrics(dynamic,ps,tokens),
                    read_dma_total=metrics(total,ps,tokens),
                    estimated_on_chip=metrics([x+y for x,y in zip(w['estimated_on_chip']['energy_nj_per_window'],total)],ps,tokens),
                    estimated_on_chip_plus_ddr=metrics([x+y for x,y in zip(w['estimated_on_chip_plus_ddr']['energy_nj_per_window'],total)],ps,tokens))
            result['scenarios'][variant]=dict(coefficient=c,windows=windows)
        dest=out/path.name;dest.write_text(json.dumps(result,indent=2)+'\n')
        index.append(dict(model=base['model'],phase=base['phase'],variants=list(coefficients),sha256=digest(dest)))
    (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    print('DMA_SCENARIO_LEDGER_PASS',len(coefficients),len(index))

if __name__=='__main__':main()
