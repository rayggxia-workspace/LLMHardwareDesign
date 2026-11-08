"""Paired extraction of explicitly identified native electrodes, no rerouting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--shards',type=int,default=8)
    p.add_argument('--masters')
    p.add_argument('--offset',type=float,default=.125)
    p.add_argument('--walks',type=int,default=262144)
    p.add_argument('--out',type=Path,default=Path(os.environ.get('LOWER_OUT','.')))
    a=p.parse_args();a.out.mkdir()
    meta=json.loads((a.scene/'scene.json').read_text());build=json.loads((a.build/'build.json').read_text())
    assert build.get('source_net_restricted_origin'), (
        'Legacy sparse source partitions are withdrawn. Existing whole-C rows '
        'remain usable; current independent checks use the corrected native_field reporter.')
    assert meta['exact_box_matches'] and meta['conductor_coordinates_order_and_ownership_unchanged']
    assert build['all_controls_passed'] and build['solver_algorithm_unchanged']
    assert sha(a.build/'lower_field')==build['binary_sha256']
    index=int(os.environ.get('LOWER_INDEX','0'));assert 0<=index<a.shards
    ids=list(map(int,a.masters.split(','))) if a.masters else meta['master_ids'][index::a.shards]
    assert ids and len(set(ids))==len(ids) and set(ids)<=set(meta['master_ids'])
    masters=a.out/'masters.txt';masters.write_text('\n'.join(map(str,ids))+'\n')
    runs={}
    for name in ['without-upper','with-upper']:
        scene=a.scene/(name+'.bin');assert sha(scene)==meta['files'][name+'.bin']['sha256']
        rows=a.out/(name+'.jsonl')
        command=[str(a.build/'lower_field'),str(scene),str(masters),os.environ['LOWER_CPUS'],str(a.walks),str(a.offset),'104729']
        with rows.open('xb') as stdout,(a.out/(name+'.log')).open('xb') as stderr:
            subprocess.run(command,stdout=stdout,stderr=stderr,check=True)
        loaded=[];maximum=0.
        with rows.open() as f:
            for line in f:
                r=json.loads(line);loaded.append(r['master']);assert r['total_ff']>0
                assert abs(sum(v[1] for v in r['values']))<1e-8*r['total_ff']
                diagonal=next(v for v in r['values'] if v[0]==r['master'])
                assert diagonal[1]==r['total_ff'] and abs(diagonal[3])<1e-12
                maximum=max(maximum,r['sigma_ff']/r['total_ff'])
        assert ids==loaded
        runs[name]=dict(path=str(rows),sha256=sha(rows),bytes=rows.stat().st_size,maximum_relative_standard_error=maximum)
    report=dict(scene=str(a.scene),scene_metadata_sha256=sha(a.scene/'scene.json'),build=str(a.build),build_metadata_sha256=sha(a.build/'build.json'),
        solver_sha256=build['binary_sha256'],masters=ids,shard=index,shards=a.shards,offset=a.offset,minimum_walks=a.walks,
        runs=runs,all_total_statistical_gates=all(v['maximum_relative_standard_error']<=.003 for v in runs.values()),
        both_scenes_same_native_geometry=True,quiet_other_electrodes=True,
        scope='Native metal-only conductor capacitance before/after actual upper geometry. Sparse unobserved mutual terms are not proven zero; not node-resolved RC or device capacitance.')
    (a.out/'solve.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='masters'}),flush=True)


if __name__=='__main__':main()
