"""Bounded A/C route or full receive/function groups in one allocation."""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from native_allocation_group import file_sha,memory_snapshot


def verify(root,out,cpus,qualify=False):
    if qualify:
        assert cpus==64
        specs=[('native-viaonly-'+role+'-transaction6k-'+policy,proof)
               for role,proof in [('receive','native-physical-receiver.json'),('final','native-final-function.json')]
               for policy in ['a','c']]
    else:
        assert cpus==32
        specs=[('native-viaonly-run-transaction6k-'+policy,'native-candidate.json')for policy in ['a','c']]
    memory=memory_snapshot()
    if qualify:
        # Four independent T6K receiver/final-cell regressions. Prior full
        # T6K gate peaks were ~20GiB; allow 32GiB per child plus 20% headroom.
        parallel=next((n for n in [4,2,1]if memory['MemAvailable']>=n*32*1024**3*1.2),1)
    else:parallel=2 if memory['MemAvailable']>=64*1024**3 else 1
    assert 16*parallel<=cpus and 16*len(specs)==cpus
    def execute(spec):
        mode,proof_name=spec;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        env=dict(os.environ,OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        started=time.time()
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'16'],
                                cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        receipt=folder/'receipt.json';proof=folder/proof_name
        r=json.loads(receipt.read_text())if receipt.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and proof.exists())
        if passed:
            p=json.loads(proof.read_text())
            passed=r['cpus']==16 and r['mode']==mode and r['outputs'][proof.name]==file_sha(proof)
            passed=passed and (p.get('passed')is True if qualify else p['pipeline_completed']is True)
        return dict(mode=mode,policy=mode[-1].upper(),cpus=16,started=started,finished=time.time(),returncode=code,passed=passed,
                    folder=str(folder),receipt_sha256=file_sha(receipt)if receipt.exists()else None,
                    proof_name=proof_name,proof_sha256=file_sha(proof)if proof.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,specs))
    result=dict(schema='block-v1-native-via-qualification-group/1'if qualify else'block-v1-native-via-route-group/1',passed=all(row['passed']for row in children),
                allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=parallel*16,memory_preflight=memory,children=children,
                qualified_hard_macro=False,scope='Two full route/final prefabrication attempts on original A/C pins; all independent physical/function/macro gates remain required')
    if qualify:result['scope']='Four independent full native physical receivers and exact final-cell regressions for A/C; no macro-boundary or twelve-layer qualification'
    (out/('native-via-qualification-group.json'if qualify else'native-via-route-group.json')).write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Route child failed; completed peer evidence retained'
