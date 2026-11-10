"""Offline audit of immutable quality, finite RTL and SystemC receipts."""
import argparse
import hashlib
import json
from pathlib import Path
from report import contents


def summarize(root):
    failures={20,21,24,26,28,30,36,39};packages={};members=0;states=[]
    for tag in range(20,42):
        folder=root/f'run{tag}';files=contents(folder);members+=len(files)-1
        index=json.loads(files['evidence-index.json']);packages[tag]=files
        jobs=index['jobs'];assert len(jobs)==1
        assert jobs[0][1]==('FAILED' if tag in failures else 'COMPLETED')
        states.append(dict(run=tag,job=jobs[0][0],state=jobs[0][1],source=index['source_commit']))
    def read(tag,name):return json.loads(packages[tag][name])
    q=read(38,'quality/closure-quality.json');rtl=read(41,'results/closure-backend.json')
    timing=read(40,'results/closure-backend.json');assert q['passed'] and rtl['passed'] and timing['passed']
    prior=read(34,'quality/closure-quality.json');failed_quality=read(29,'quality/closure-quality.json')
    assert not prior['profiles'][0]['public_reference_study_admitted']
    assert not failed_quality['profiles'][0]['public_reference_study_admitted']
    assert q['artifact']['revision']=='1fed15cb34975bc0bd699e62b95a539bb06eed42'
    assert q['head']['weight_group']==16 and q['head']['embedding_lookup_bits']==16
    assert len(q['FFN'])==4 and all(x['bounded_down_bit_exact'] for x in q['FFN'])
    assert max(x['output_relative_L2'] for x in q['FFN'])<.001
    source22=read(22,'quality/closure-quality.json')
    for name in ('closure-m-vectors.txt','closure-g-vectors.txt','g32-lut.hex'):
        assert q['retained_artifacts'][name]['sha256']==source22['retained_artifacts'][name]['sha256']
    assert rtl['quality_sha256']==hashlib.sha256(packages[22]['quality/closure-quality.json']).hexdigest()
    assert [x['packets'] for x in rtl['G32']]==[2048,2048] and rtl['M']['packets']==192
    assert rtl['partial']['checks']==600 and rtl['controller']['checks']==600
    assert rtl['context']['checks']==1025 and rtl['finalize']['checks']==1200
    assert [x['checks'] for x in rtl['weight_banks']]==[48,96,192]
    assert rtl['contract']['passed'] and rtl['contract']['record_checks']==24
    cases=[]
    for c in timing['cases']:
        r=c['result'];cl=r['closure'];assert cl['head_weight_group']==16
        assert r['P_scratch_peak_bytes']<=16384 and cl['S_peak']<=16384 and cl['bank_peak']<=c['knobs']['CL_BANKS']
        assert not cl['physical_qualified']
        cases.append(dict(name=c['name'],tokens_s=r['tokens_per_second'],ms_per_token=1000/r['tokens_per_second'],
            spans_ms={k:v/300000 for k,v in r['spans_ticks'].items()},read_bus_bytes=r['read_bus_bytes'],
            write_bus_bytes=r['write_bus_bytes'],closure=cl,knobs=c['knobs']))
    best=max((c for c in cases if c['name'].startswith('decode512')),key=lambda c:c['tokens_s'])
    same=next(c for c in cases if c['name']=='decode512-mode5-issue2-bw102400-banks4')
    p=q['profiles'][0];assert p['bits']==16 and p['group']==128
    assert not q['profiles'][1]['public_reference_study_admitted']
    result=dict(passed=True,packages=len(packages),verified_members=members,runs=states,
        public_model=q['artifact'],quality_scope=q['scope'],quality_thresholds=q['admission_thresholds'],
        selected_quality={k:p[k] for k in ('name','PPL_ratio','mean_KL','top1_fraction','vs_official','decode512','numerical_study_admitted','public_reference_study_admitted')},
        failed_head128=failed_quality['profiles'][0]['vs_official'],failed_head32=prior['profiles'][0]['vs_official'],
        FFN=q['FFN'],RTL=rtl,cases=cases,best=best,
        same_resource_streaming_gain=best['tokens_s']/same['tokens_s']-1,
        full_integer_LLM=False,physical_qualified=False,production_RTL_modified=False,
        native_full_model_tokens_s=None,energy_J_token=None,
        qualification='conditional SystemC timing + float-attention/RMS quality screen + separate finite integer/RTL services; not integrated model execution or physical signoff')
    (root/'summary.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return {k:result[k] for k in ('passed','packages','verified_members','same_resource_streaming_gain','native_full_model_tokens_s')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    print(json.dumps(summarize(p.parse_args().root)))
