"""Verify evidence hashes, paired numerical outputs, covered sums and units."""
from pathlib import Path
from hashlib import sha256
import json,math
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_bytes())
def close(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)
def main():
    data=load(R/'results-200mhz.json');assert not data['missing_models'] and len(data['models'])==7
    manifest=load(R/'results/accepted-manifest.json')
    samples={}
    for rel,h in manifest.items():
        p=R/'results'/rel;assert sha256(p.read_bytes()).hexdigest()==h
        x=load(p);assert x['passed'] and x['core_ps'] in (3334,5000) and x['ddr_tick_ps']==630
        samples[x['model'],x['phase'],x['core_ps']]=x
    checks=0
    for row in data['models']:
        for phase in ('prefill','decode'):
            a,b=[samples[row['model'],phase,period] for period in (3334,5000)]
            assert a['numerical']==b['numerical']
            assert a['input_sha256']==b['input_sha256']
            for s,t in zip(a['segments'],b['segments']):
                assert (s['kind'],s['step'],s['layer'])==(t['kind'],t['step'],t['layer'])
                if 'output_sha256' in s:assert s['output_sha256']==t['output_sha256']
            w=row['windows'][phase];t=w['duration_s'];n=w['tokens']
            close(n/t,w['tokens_per_second'])
            for edge in (0,1):
                chip=sum(v[edge] for k,v in w['components_j'].items() if k!='ddr_devices')
                total=chip+w['components_j']['ddr_devices'][edge]
                for scope,e in [('on_chip',chip),('on_chip_plus_ddr',total)]:
                    s=w['scopes'][scope]
                    close(e,s['energy_j_per_window'][edge]);close(e/n,s['energy_j_per_token'][edge]);close(e/t,s['average_power_w'][edge]);close(n/e,s['tokens_per_joule'][1-edge])
                    assert all(0<v[0]<=v[1] for v in s.values())
            for k in w['components_j']:
                if 'idle' in k or 'quiet' in k or 'core_reference' in k:assert k in w['resident_reintegration'],k
            checks+=1
    output={'passed':True,'models':7,'windows':checks,'paired_numerical_layers':sum(r['numerical_layer_checks'] for r in data['models']),
        'accepted_sample_files':len(samples),'server_output_hashes_verified':True,'paired_outputs_equal':True,
        'component_sums_and_units_verified':True,'full_model_200_error_measured':False,'full_prefill512_error_measured':False}
    (R/'validation.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output))
if __name__=='__main__':main()
