"""Fill only missing before/after native-interface rows, reusing valid samples.

This covers native branches of all original upper-connected nets. It does not
claim coverage of internal signals which have no original upper connection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE=Path('/public/home/yuzelu/PingyangHuang')
SCENE=BASE/'issue-222-coupling-DuSb4uk1/job-100170/result'
SAMPLE=BASE/'issue-222-validated-mPI4CdbA/job-100246/result'
BUILD=BASE/'issue-222-merge-fix-OLZaDNeN/job-100237/build'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shards',type=int,default=4)
    p.add_argument('--out',type=Path,default=Path(os.environ.get('LOWER_OUT','.')))
    a=p.parse_args();index=int(os.environ.get('LOWER_INDEX','0'));assert 0<=index<a.shards
    a.out.mkdir()
    meta=json.loads((SCENE/'scene.json').read_text());sample=json.loads((SAMPLE/'macro-boundary.json').read_text())
    build=json.loads((BUILD/'build.json').read_text())
    assert build.get('source_net_restricted_origin'), (
        'Legacy source partitions are withdrawn. Use lower_split_run.py; '
        'completed old whole-C rows can be recovered with lower_before_reuse.py.')
    assert sample['surface_interval_merge_fixed'] and sample['offset']==.25
    assert sample['original_scene_sha256']==meta['scene_sha256']
    assert sample['solver_sha256']==build['binary_sha256']==sha(BUILD/'native_field')
    assert sample['macro_includes_shared_m10'] and sample['conductor_geometry_unchanged']
    inherited={}
    for label in ['without-upper','with-upper']:
        path=SAMPLE/(label+'.jsonl');items={}
        for line in path.read_text().splitlines():
            r=json.loads(line);assert r['master'] not in items;items[r['master']]=r
        inherited[label]=items
    assert set(inherited['without-upper'])==set(inherited['with-upper'])
    todo=[i for i in range(index,2491,a.shards) if i not in inherited['without-upper']]
    assert todo
    masters=a.out/'masters.txt';masters.write_text('\n'.join(map(str,todo))+'\n')
    sources={'without-upper':SCENE/'lower-only.bin','with-upper':SAMPLE/'macro-owned-m10.bin'}
    expected={'without-upper':meta['lower_scene_sha256'],'with-upper':sample['macro_accounting_scene_sha256']}
    result={}
    for label,path in sources.items():
        assert sha(path)==expected[label]
        target=a.out/(label+'.jsonl')
        command=[str(BUILD/'native_field'),str(path),str(masters),os.environ['LOWER_CPUS'],'1048576','.25','104729']
        with target.open('xb') as out,(a.out/(label+'.log')).open('xb') as err:
            subprocess.run(command,stdout=out,stderr=err,check=True)
        ids=[];max_error=0.
        with target.open() as f:
            for line in f:
                r=json.loads(line);ids.append(r['master'])
                assert r['net']=='word_'+format(r['master'],'04')
                assert r['total_ff']>0 and abs(sum(v[0] for v in r['values']))<1e-8*r['total_ff']
                max_error=max(max_error,r['sigma_ff']/r['total_ff'])
        assert ids==todo
        result[label]=dict(scene=str(path),scene_sha256=expected[label],rows_sha256=sha(target),maximum_relative_total_standard_error=max_error)
    receipt=dict(shard=index,shards=a.shards,masters=todo,reused_masters=sorted(inherited['without-upper']),
        reuse_directory=str(SAMPLE),reuse_metadata_sha256=sha(SAMPLE/'macro-boundary.json'),
        reused_rows={label:dict(path=str(SAMPLE/(label+'.jsonl')),sha256=sha(SAMPLE/(label+'.jsonl'))) for label in sources},
        runs=result,solver_sha256=build['binary_sha256'],offset=.25,minimum_walks=1048576,
        macro_owns_all_m10=True,all_native_layers_present=True,
        scope='Paired metal-only native-branch charge on original 2491 interface conductors, both macro ends summed; not all internal nets or node-resolved SPEF.')
    (a.out/'interface.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
