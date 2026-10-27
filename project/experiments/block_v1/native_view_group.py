"""Four source-qualified candidate views in one bounded c96 allocation.

Physical receiver success remains mandatory for each child. Generated Liberty
and LEF remain candidates until separate flat/abstract boundary qualification.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from native_allocation_group import file_sha,memory_snapshot


def verify(root,out,cpus,escape_only=False):
    assert cpus==(16 if escape_only else 32)
    specs=[(('native-escape-view-'if escape_only else'native-prefab-view-')+top+'-'+policy,top,policy.upper())
           for top in (['transaction6k']if escape_only else['shared109','transaction6k'])for policy in ['a','c']]
    memory=memory_snapshot()
    # Deliberately use the observed ~172GiB full C8 peak for every child.
    # A view-only peak has not been measured; no lower estimate is asserted.
    prior_peak=180451804*1024
    simultaneous=next((n for n in [len(specs),1]if memory['MemAvailable']>=n*prior_peak*1.2),1)if escape_only else next((n for n in [4,2,1]if memory['MemAvailable']>=n*prior_peak*1.2),1)
    def execute(spec):
        mode,top,policy=spec;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        started=time.time()
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'8'],
                                cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        receipt=folder/'receipt.json';proof=folder/'native-view-generation.json'
        record=dict(mode=mode,top=top,policy=policy,cpus=8,returncode=code,started=started,finished=time.time(),passed=False)
        try:
            bound=json.loads(receipt.read_text());result=json.loads(proof.read_text())
            record.update(receipt_sha256=file_sha(receipt),proof_sha256=file_sha(proof))
            record['passed']=bool(code==0 and bound['passed']is True and bound['mode']==mode and bound['cpus']==8
                                  and bound['outputs'][proof.name]==file_sha(proof) and result['passed']is True
                                  and result['top']==top and result['policy']==policy)
        except(OSError,KeyError,ValueError)as error:record['validation_error']=repr(error)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:
        children=list(pool.map(execute,specs))
    record=dict(schema='block-v1-native-view-group/1',passed=all(c['passed']for c in children),children=children,
                allocated_cpus=cpus,simultaneous_workers=simultaneous,maximum_concurrent_cpu_ceilings=8*simultaneous,
                memory_preflight=memory,prior_full_c8_peak_bytes=prior_peak,memory_safety_factor=1.2,
                qualified_hard_macro=False,
                scope=('Two complete-physical/final-function-qualified T6K candidate view generations/readbacks; no boundary timing, twelve-layer or hard-macro qualification'if escape_only else'Four same-source native-tool candidate view generations/readbacks; no boundary timing, final function, twelve-layer or hard-macro qualification'))
    (out/'native-view-group.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'A source-qualified view child failed; all completed peer receipts retained'
