"""Replace matching scalar proxies in an explicitly conditional candidate scenario.

The native RTL samples calibrate primitives, not complete model FP32 services.
Keep composite arithmetic and conversion gaps visible; never add a new primitive
on top of its old proxy. Only accepted E32-18 windows enter this ledger.
"""
from collections import defaultdict
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from seven_model_arithmetic_estimate import calibrations,operations
from six_model_tlm_power import metrics

def load(p):return json.loads(p.read_bytes())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def add(a,b):return [x+y for x,y in zip(a,b)]
def scale(a,n):return [x*n for x in a]

def replacement(kind,shape,inputs):
    """Calls to measured RTL plus residual scalar arithmetic per service."""
    n=shape.get('elements',0)
    if kind in ('gelu','sigmoid'):
        # Both frozen services multiply the nonlinear gate by the up input.
        return {kind:n},(n,0,0,0)
    if kind=='router':
        e,k=shape['experts'],shape['top']
        return {'exp':k},(0,e*k+2*k,0,k)
    if kind=='conv4':return {'conv4':shape['channels']},(0,0,0,0)
    if kind=='recurrent_factors':
        n=inputs['a_log'][0]
        calls={'exp':2*n,'softplus':n}
        if shape['gdn']:calls['sigmoid']=n
        return calls,(2*n,2*n,0,0)
    if kind=='recurrent_norm_gate':
        n=inputs['value'][0]
        return {'sigmoid':n},((5*n,2*n,0,32) if shape['gdn'] else (2*n,n,0,0))
    return None

def main():
    special=load(HERE/'special-pin-calibration.json');conv=load(HERE/'conv4-pin-calibration.json')
    for name in ('special','conv4'):
        path=HERE/(name+'-pin-calibration.json')
        assert digest(path)+'  calibration.json' in path.with_name(name+'-pin-results.sha256').read_text()
    assert special['rtl_replay_all_commands_passed']
    _,_,mul,_=calibrations()
    plus=load(HERE.parent/'no-wire-results/coefficients.json')['u_add_nj_per_word']/4
    def proxy(counts):
        m,a,t,r=counts
        return [.5*((m+4*t+4*r)*mul[0]+(a+4*t+4*r)*plus),
                2*((m+12*t+16*r)*mul[1]+(a+12*t+16*r)*plus)]
    out=HERE/'special-candidate-ledger';out.mkdir(exist_ok=True);index=[]
    for path in sorted((HERE/'timing-ledger').glob('*.json')):
        if path.stem=='index':continue
        base=load(path);model,phase=base['model'],base['phase']
        counts_path=HERE.parent/'arithmetic-model-counts'/(model+'.json')
        counts=load(counts_path)['phases'][phase]
        windows={}
        for name,w in base['windows'].items():
            old={};new={};audit=[];sites=set();conv_sites=set()
            for sig,calls in counts['operator_counts'].items():
                if sig.split(':')[0]!=name:continue
                spec=counts['operator_shapes'][sig];kind=spec['kind']
                match=replacement(kind,spec['shape'],spec['input_shapes'])
                if match is None:continue
                primitive,residual=match;native=0.
                for op,n in primitive.items():
                    if op=='conv4':
                        c=conv['cases'][model+'-'+phase]
                        assert c['rtl_q_reference_equal']
                        per=c['incremental_nj_per_channel']
                        conv_sites.add(int(sig.split(':site')[1].split(':')[0]))
                    else:
                        per=special['primitives'][op]['incremental_nj_per_call']
                        sites.add(int(sig.split(':site')[1].split(':')[0]))
                    native+=per*n*calls
                key='proxy_'+kind
                old[key]=add(old.get(key,[0.,0.]),scale(proxy(operations(kind,spec['shape'],spec['input_shapes'])),calls))
                # Retain the pre-existing 0.5x..2x transfer sensitivity for
                # extrapolation to unsampled values and missing FP32 hardware.
                replacement_energy=add([.5*native,2*native],scale(proxy(residual),calls))
                new[key]=add(new.get(key,[0.,0.]),replacement_energy)
                audit.append(dict(signature=sig,service_calls=calls,rtl_primitive_calls_per_service=primitive,
                    measured_candidate_dynamic_nj=native,residual_arithmetic_per_service=residual,
                    residual_is_operation_proxy=True))
            ps,tokens=w['elapsed_ps'],w['tokens']
            for key,value in old.items():
                assert all(isclose(a,b,rel_tol=1e-12,abs_tol=1e-7) for a,b in zip(value,w['components'][key]['energy_nj_per_window'])),(model,name,key)
            # Candidate deployment scenario: one unit per site that actually
            # calls it, always clocked. This is a proposed binding, not a top.
            special_idle=[r['power']['idle']['power_w']['total'] for r in special['primitives'].values()]
            conv_idle=[r['power']['idle']['power_w']['total'] for r in conv['cases'].values()]
            idle=[(len(sites)*f(special_idle)+len(conv_sites)*f(conv_idle))*ps/1000 for f in (min,max)]
            subtotal=[sum(v[e] for k,v in ((k,r['energy_nj_per_window']) for k,r in w['components'].items()) if k not in old)
                      +sum(v[e] for v in new.values())+idle[e] for e in (0,1)]
            ddr=w['ddr']['energy_nj_per_window']
            windows[name]=dict(elapsed_ps=ps,tokens=tokens,removed_proxies={k:metrics(v,ps,tokens) for k,v in old.items()},
                replacement_components={k:metrics(v,ps,tokens) for k,v in new.items()},
                candidate_idle=metrics(idle,ps,tokens),proposed_special_sites=sorted(sites),proposed_conv4_sites=sorted(conv_sites),
                arithmetic_mapping=audit,estimated_on_chip=metrics(subtotal,ps,tokens),
                estimated_on_chip_plus_ddr=metrics(add(subtotal,ddr),ps,tokens),dma_scenarios={})
            dma_path=HERE/'dma-ledger'/path.name
            if dma_path.exists():
                for variant,scenario in load(dma_path)['scenarios'].items():
                    dm=scenario['windows'][name]['read_dma_total']['energy_nj_per_window']
                    windows[name]['dma_scenarios'][variant]=dict(
                        estimated_on_chip=metrics(add(subtotal,dm),ps,tokens),
                        estimated_on_chip_plus_ddr=metrics(add(add(subtotal,ddr),dm),ps,tokens))
        result=dict(model=model,phase=phase,windows=windows,
            estimator_sha256=digest(Path(__file__)),
            scope='Conditional candidate replacement scenario, not default accepted model RTL',
            target_clock_mhz=300,sram_bits=512,wire_parasitics_loaded=False,
            rtl_full_model_numeric_accepted=False,physical_binding_accepted=False,
            timing_recomputed_for_candidate_service=False,
            assumptions=['Use accepted E32-18 model timing; new candidate service timing is not installed in the model',
                'One always-clocked candidate per used TLM site is a proposed footprint, not actual physical deployment',
                'Measured primitive dynamic energy replaces its old proxy exactly once; residual composite arithmetic retains proxies',
                '0.5x..2x is an assumed transfer sensitivity, not a confidence interval or a measured error bound',
                'Existing G32, RMS, softmax, RoPE and SRAM work are preserved without adding E32 twice'],
            still_missing=['FP32 conversions and provider-to-port adapters',
                'Complete composite multiply/divide/normalization and recurrent state RTL integration',
                'Actual instantiated topology/gating and full model RTL state residence',
                'Candidate-cycle and shared-resource model rescheduling; no new throughput acceptance'],
            inputs={str(p.relative_to(HERE.parent)):digest(p) for p in
                (path,counts_path,HERE/'special-pin-calibration.json',HERE/'conv4-pin-calibration.json')})
        dest=out/path.name;dest.write_text(json.dumps(result,indent=2)+'\n')
        index.append(dict(model=model,phase=phase,sha256=digest(dest)))
    (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    print('SPECIAL_CANDIDATE_LEDGER_PASS',len(index))

if __name__=='__main__':main()
