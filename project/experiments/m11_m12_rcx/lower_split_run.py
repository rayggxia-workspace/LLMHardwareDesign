"""Corrected native/upper source accounting, filling only missing before rows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE=Path('/public/home/yuzelu/PingyangHuang')
SCENE=BASE/'issue-222-coupling-DuSb4uk1/job-100170/result'
ORIGINAL=BASE/'issue-222-validated-mPI4CdbA/job-100247/result'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--reuse',type=Path,required=True);p.add_argument('--shards',type=int,default=4);a=p.parse_args()
    out=Path(os.environ['LOWER_OUT']);out.mkdir();index=int(os.environ.get('LOWER_INDEX','0'))
    assert 0<=index<a.shards;ids=list(range(index,2491,a.shards))
    build=json.loads((a.build/'build.json').read_text());reuse=json.loads(a.reuse.read_text());meta=json.loads((SCENE/'scene.json').read_text())
    assert build['source_net_restricted_origin'] and build['all_controls_passed']
    missing=[i for i in ids if str(i) not in reuse['rows'] or not reuse['rows'][str(i)]['statistical_gate']]
    output={}
    for label,masters,binary,scene,minimum in [('before-missing',missing,'native_field',SCENE/'lower-only.bin',1048576),('after-corrected',ids,'lower_split_field',SCENE/'scene.bin',262144)]:
        if not masters:continue
        assert sha(a.build/binary)==build['binary_sha256'][binary]
        assert sha(scene)==meta['lower_scene_sha256' if label=='before-missing' else 'scene_sha256']
        listing=out/(label+'-masters.txt');listing.write_text('\n'.join(map(str,masters))+'\n')
        target=out/(label+'.jsonl')
        with target.open('xb') as stdout,(out/(label+'.log')).open('xb') as stderr:
            subprocess.run([str(a.build/binary),str(scene),str(listing),os.environ['LOWER_CPUS'],str(minimum),'.25','104729'],stdout=stdout,stderr=stderr,check=True)
        loaded=[];maximum=0.
        with target.open() as f:
            for line in f:
                r=json.loads(line);loaded.append(r['master']);assert r['total_ff']>0
                assert abs(sum(v[0] for v in r['values']))<1e-8*r['total_ff']
                maximum=max(maximum,r['sigma_ff']/r['total_ff'])
                if label=='after-corrected':assert len(r['values'][0])==8
        assert loaded==masters;output[label]=dict(path=str(target),sha256=sha(target),rows=len(loaded),maximum_relative_total_standard_error=maximum)
    # Changed reporting must leave the complete physical matrix untouched.
    original={}
    with (ORIGINAL/'rows.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['master'] in ids:original[r['master']]=r
    checked=0
    with (out/'after-corrected.jsonl').open() as f:
        for line in f:
            r=json.loads(line);old=original[r['master']]
            assert all(r[k]==old[k] for k in ['walks','hops','total_ff','sigma_ff','ground'])
            assert [[v[0],v[1]] for v in r['values']]==[[v[0],v[1]] for v in old['values']]
            checked+=1
    result=dict(shard=index,shards=a.shards,masters=ids,computed_before_ids=missing,
        reused_before_ids=[i for i in ids if i not in missing],reuse_file=str(a.reuse),reuse_sha256=sha(a.reuse),
        build=str(a.build),build_metadata_sha256=sha(a.build/'build.json'),source_scene_metadata_sha256=sha(SCENE/'scene.json'),
        output=output,whole_field_exactly_matches_old_valid_matrix=checked,
        source_bins=['upper_above_m10','shared_m10_landing','other_native'],source_net_restricted_origin=True,
        macro_native_charge='shared_m10_landing + other_native',parent_compatible_upper_charge='upper_above_m10 + shared_m10_landing',
        warning='The two ownership views share M10 landing; never sum them. A disjoint full charge uses all three bins once.')
    (out/'split.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not k.endswith('_ids') and k!='masters'}),flush=True)

if __name__=='__main__':main()
