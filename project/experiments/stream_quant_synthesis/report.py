"""Derive compact comparisons from verified receipts, never hand-edit timings."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import collect
import planner


def contents(folder):
    collect.verify(folder)
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode((folder/'evidence.tar.gz.b64').read_bytes())),mode='r:gz') as tar:
        return {m.name:tar.extractfile(m).read() for m in tar.getmembers()}


def report(root,tag,quality_tag):
    files=contents(root/('run'+tag));r=json.loads(files['results/result.json'])
    assert r['passed'] and len(r['cases'])==65
    assert len(r['rounds']['requant_RTL'])==3
    for x in r['rounds']['RTL']:
        assert x['frames']==44 and x['packets']>5691
    assert sum(c.get('exact_R4_baseline',False) for c in r['cases'])==12
    cases=[]
    for c in r['cases']:
        v=c['result'];baseline=next(x for x in r['cases'] if x['name']=='off-'+c['workload']+'-0')['result']
        cases.append(dict(name=c['name'],knobs=c['knobs'],tokens_s=v['tokens_per_second'],
                          ms_per_output_token=1000/v['tokens_per_second'],
                          relative_to_shared_baseline=v['tokens_per_second']/baseline['tokens_per_second']-1,
                          bus_GB_s=c['average_bus_GB_s'],read_bytes=v['read_bus_bytes'],write_bytes=v['write_bus_bytes'],
                          S_peak=v['P_scratch_peak_bytes'],sq=v.get('sq_study')))
    assert all(c['S_peak']<=16384 for c in cases)
    quality_files=contents(root/('run'+quality_tag));quality=json.loads(quality_files['quality/quality.json'])
    screening=[dict(bits=x['activation_bits'],policy=x['activation_policy'],weight_scale=x['weight_scale_policy'],
                    cosine=[y['cosine'] for y in x['metrics']],top1_match=[y['top1_match'] for y in x['metrics']]) for x in quality['rows']]
    # Re-emit requirements using actual case beat width, independently of old metadata.
    # Executed text plans must remain byte-for-byte unchanged; this is NOT binary ISA.
    bundles={}
    for name,data in files.items():
        if not name.startswith('results/plan-') or not name.endswith('.json'):continue
        plan=json.loads(data);coupled='coupled' in name
        bits=8 if 'coupled-a8-' in name else 16 if 'coupled-a16-' in name else 0
        destination=root/('bundle-'+Path(name).name[5:]);planner.bundle(plan,destination,3 if coupled else 2,bits,64)
        text=''.join('%s %s %s\n'%tuple(x['action']) for x in plan['rows']).encode()
        assert text==files[name[:-5]+'.txt']
        bundles[destination.name]=hashlib.sha256(destination.read_bytes()).hexdigest()
    out=dict(source_commit=r['source_commit'],Slurm_job=r['Slurm_job'],model_cases=len(cases),
             exact_baseline_checks=12,RTL=r['rounds']['RTL'],requant_RTL=r['rounds']['requant_RTL'],DP_checks=r['rounds']['DP_checks'],
             quality_source_commit=json.loads(quality_files['evidence-index.json'])['source_commit'],
             quality_job=quality['job'],quality_scope=quality['scope'],quality_screening=screening,
             cases=cases,reemitted_operand_requirements=bundles,
             energy_J_per_token=None,native_full_model_tokens_s=None,physical_frequency_qualified=False)
    (root/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',default='12');p.add_argument('--quality-run',default='08')
    a=p.parse_args();r=report(a.root,a.run,a.quality_run)
    print(json.dumps(dict(cases=r['model_cases'],baseline_checks=r['exact_baseline_checks'],bundles=len(r['reemitted_operand_requirements']))))
