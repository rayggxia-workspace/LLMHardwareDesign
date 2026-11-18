"""Audit accepted per-model TLM deployment without inventing physical bindings."""
from hashlib import sha256
import json
from pathlib import Path
import sys

def digest(p):return sha256(p.read_bytes()).hexdigest()
def main():
    source,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=True);summary=[]
    for folder in sorted(source.iterdir()):
        if not folder.is_dir():continue
        stage=folder/'result';accept=json.loads((stage/'acceptance.json').read_text())
        assert accept['passed'] and accept['numerical_files_equal'] and accept['ddr_terminal_reconciled']
        d=json.loads((stage/'deployment-observation.json').read_text());result=json.loads((stage/'result.json').read_text())
        assert d['data_sram_bits']==512 and d['core_period_ps']==3334
        registry={tuple(row['key']):row for row in d['bindings']};assert len(registry)==len(d['bindings'])
        windows={};used=set()
        for name,w in d['windows'].items():
            if name=='outside':continue
            duration=w['elapsed_ps'];assert duration==w['end_ps']-w['start_ps'] and duration>0
            calls={site:0 for site in range(4)};routes=[]
            for signature,count in w['routes'].items():
                key=tuple(map(int,signature.split('/')));assert key in registry and count>0
                calls[key[0]]+=count;used.add(key)
                routes.append(dict(key=list(key),calls=count,provider=registry[key]['provider'],module=registry[key]['module']))
            for site,n in calls.items():assert n==w['counters'].get('local_calls_site%d'%site,0)
            occupancy={}
            for key,row in w['resources'].items():
                busy=row['busy_union_ps'];assert 0<=busy<=duration
                if key.endswith(('_E32','_Mshared')) or key.startswith(('provider_site','local_target_')):
                    assert row['overlapping_request_ps']==0,(folder,key,row)
                occupancy[key]=dict(busy_ps=busy,idle_or_other_ps=duration-busy,duty=busy/duration,calls=row['calls'],
                    overlap_ps=row['overlapping_request_ps'],source='exact TLM interval union, not RTL state encoding')
            windows[name]=dict(elapsed_ps=duration,local_calls_by_site=calls,routes=routes,occupancy=occupancy,
                control_counters=w['counters'],gating_savings_nj=0)
        manifest=dict(model=result['model'],phase=result['mode'],variant=folder.name.split('-',2)[2],
            e32_product_cycles=d['calibrated_e32_product_cycles'],core_period_ps=3334,data_sram_bits=512,
            bindings=[registry[k] for k in sorted(used)],registered_but_unused=[registry[k] for k in sorted(set(registry)-used)],
            windows=windows,clock_policy='all reference instances remain clocked; no physical clock/power gating evidence',
            evidence=dict(acceptance=digest(stage/'acceptance.json'),deployment=digest(stage/'deployment-observation.json'),
                result=digest(stage/'result.json'),provenance=digest(folder/'provenance.json')),
            proven=['actual executed provider keys, service counts, PM installs, instruction counts and callback intervals',
                'no overlap at each local target/provider and at shared E32/M resources during these accepted windows'],
            still_unverified=['per-model complete RTL top, concrete provider-to-port wiring and matching router parameters',
                'complete-model mother/LC state traces and physical clock gating; C639 state traces are a reference only',
                'special candidate units are not automatically installed into the frozen model datapath'])
        dest=out/(folder.name+'.json');dest.write_text(json.dumps(manifest,indent=2)+'\n')
        summary.append(dict(model=result['model'],phase=result['mode'],directory=folder.name,cycles=d['calibrated_e32_product_cycles'],
            routes=len(used),artifact_sha256=digest(dest),full_physical_binding_accepted=False))
    (out/'index.json').write_text(json.dumps(dict(entries=summary,scope='accepted executable bindings and exact TLM resource residence; physical deployment gaps remain'),indent=2)+'\n')
    print('DEPLOYMENT_AUDIT_PASS',len(summary),flush=True)
if __name__=='__main__':main()
