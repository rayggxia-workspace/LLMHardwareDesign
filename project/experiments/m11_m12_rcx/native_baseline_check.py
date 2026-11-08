"""Validate the merge fix against saved original rows; do not rerun all baseline."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from native_compare import BASE
from native_scene import write
from native_shared_reference import UPPER, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--masters',required=True)
    a=p.parse_args();build=json.loads((a.build/'build.json').read_text())
    assert build['bidirectional_interval_merge']
    solver=a.build/'native_field';assert sha(solver)==build['binary_sha256']
    upper=json.loads(UPPER.read_text());ids=[int(x) for x in a.masters.split(',')]
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    scene=out/'baseline-geometry.bin'
    write(scene,[r['name'] for r in upper],((i,0,b) for i,r in enumerate(upper) for b in r['boxes']))
    masters=out/'masters.txt';masters.write_text('\n'.join(map(str,ids))+'\n')
    with (out/'rows.jsonl').open('xb') as stdout,(out/'field.log').open('xb') as stderr:
        subprocess.run([str(solver),str(scene),str(masters),os.environ['COUPLING_THREADS'],
                        '262144','.25','104729'],stdout=stdout,stderr=stderr,check=True)
    shards=json.loads((BASE/'assembly.json').read_text())['shards'];records=[]
    with (out/'rows.jsonl').open() as f:
        for line in f:
            row=json.loads(line);i=row['master']
            original=Path(shards[str(i%16)]['path']).parent/('row-'+format(i,'03')+'.json')
            saved=json.loads(original.read_text());old,old_sigma=saved['values'][i]
            delta=row['total_ff']-old;bound=row['sigma_ff']+old_sigma
            assert abs(row['values'][i][4])<1e-10
            records.append(dict(master=i,old_total_ff=old,new_total_ff=row['total_ff'],
                                delta_ff=delta,delta_percent=100*delta/old,
                                conservative_sigma_ff=bound,within_six_sigma=(abs(delta)<=6*bound)))
    assert [r['master'] for r in records]==ids
    report=dict(passed=all(r['within_six_sigma'] for r in records),sampled_nets=len(ids),
                original_whole_baseline_reused=True,original_upper_sha256=sha(UPPER),
                fixed_solver_sha256=build['binary_sha256'],records=records,
                scope='Seven-row solver compatibility check. Saved original complete SPEF and all original jobs remain untouched.')
    (out/'baseline-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));assert report['passed']


if __name__=='__main__':main()
