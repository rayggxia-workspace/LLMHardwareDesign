"""Two planned T6K pin policies, each 16 CPU, in one 32-CPU allocation."""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from native_allocation_group import file_sha,memory_snapshot


def verify(root,out,cpus):
    assert cpus==32
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=64*1024**3 else 1
    def execute(policy):
        mode='native-viaonly-run-transaction6k-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        env=dict(os.environ,OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        started=time.time()
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'16'],
                                cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        receipt=folder/'receipt.json';proof=folder/'native-candidate.json'
        r=json.loads(receipt.read_text())if receipt.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and proof.exists())
        if passed:
            p=json.loads(proof.read_text())
            passed=r['cpus']==16 and r['mode']==mode and r['outputs'][proof.name]==file_sha(proof)
            passed=passed and p['pipeline_completed']is True
        return dict(mode=mode,policy=policy.upper(),cpus=16,started=started,finished=time.time(),returncode=code,passed=passed,
                    folder=str(folder),receipt_sha256=file_sha(receipt)if receipt.exists()else None,
                    candidate_sha256=file_sha(proof)if proof.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-via-route-group/1',passed=all(row['passed']for row in children),
                allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=parallel*16,memory_preflight=memory,children=children,
                qualified_hard_macro=False,scope='Two full route/final prefabrication attempts on original A/C pins; all independent physical/function/macro gates remain required')
    (out/'native-via-route-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Route child failed; completed peer evidence retained'
