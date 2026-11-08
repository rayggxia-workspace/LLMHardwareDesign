"""Link a sparse reporter to unchanged accepted solver objects; replay controls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

SOURCE=Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099')
BUILD=Path('/public/home/yuzelu/PingyangHuang/issue-222-merge-fix-OLZaDNeN/job-100237/build')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=Path(os.environ['LOWER_OUT']);out.mkdir()
    proof=json.loads((BUILD/'build.json').read_text());assert proof['bidirectional_interval_merge']
    assert sha(BUILD/'native_field')==proof['binary_sha256']
    objects=[BUILD/'Solver.o',BUILD/'GaussianSurface.o']+[SOURCE/name for name in proof['unchanged_objects']]
    assert all(sha(SOURCE/name)==h for name,h in proof['unchanged_objects'].items())
    root=SOURCE/'src/fsv';here=Path(__file__).resolve().parent;binary=out/'lower_field'
    command=['g++','-std=c++20','-O3','-pthread','-I'+str(BUILD/'include'),'-I'+str(root/'include'),'-I'+str(root/'src'),str(here/'lower_field.cpp'),*map(str,objects),'-o',str(binary)]
    with (out/'compile.log').open('xb') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
    controls=BUILD.parent/'controls';masters=out/'masters.txt';masters.write_text('0\n')
    checked=[]
    for name in ['split-one','split-many','single-owner','separate-neighbors','common-potential','disjoint-near-equal-coordinates']:
        with (out/(name+'.jsonl')).open('xb') as stdout,(out/(name+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(controls/(name+'.bin')),str(masters),'1' if name=='split-one' else '4','262144','.125','99991'],stdout=stdout,stderr=stderr,check=True)
        before=json.loads((controls/(name+'.jsonl')).read_text());after=json.loads((out/(name+'.jsonl')).read_text())
        assert all(after[k]==before[k] for k in ['master','net','walks','hops','total_ff','sigma_ff','ground'])
        dense=[[0.]*6 for _ in before['values']]
        for i,*values in after['values']:dense[i]=values
        assert dense==before['values'],name
        checked.append(dict(case=name,exact_dense_sparse_match=True,original_rows_sha256=sha(controls/(name+'.jsonl'))))
    result=dict(binary=str(binary),binary_sha256=sha(binary),source_sha256=sha(here/'lower_field.cpp'),
        linked_objects={str(p):sha(p) for p in objects},original_solver_binary_sha256=proof['binary_sha256'],
        solver_algorithm_unchanged=True,reporter_only_sparse_output=True,controls=checked,all_controls_passed=True,
        source_net_restricted_origin=False,source_partitions_qualified=False,
        qualification='Legacy whole-matrix sparse reporter only. Source partitions are withdrawn; do not use for new source accounting.')
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
