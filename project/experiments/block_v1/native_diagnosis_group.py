"""Two bounded read-only physical diagnostics in one c96 allocation."""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from native_allocation_group import file_sha,memory_snapshot


def verify(root,out,cpus):
    assert cpus==16
    specs=[('native-diode2-drc-locate-a','native-drc-location.json'),
           ('native-passive-endpoint-probe','native-passive-endpoint-probe.json')]
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=48*1024**3 else 1
    def execute(spec):
        mode,proof=spec;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        started=time.time()
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'8'],
                                cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        receipt_path=folder/'receipt.json';proof_path=folder/proof
        receipt=json.loads(receipt_path.read_text())if receipt_path.exists()else{}
        passed=bool(code==0 and receipt.get('passed')is True and proof_path.exists())
        if passed:
            passed=receipt['cpus']==8 and receipt['mode']==mode and receipt['outputs'][proof]==file_sha(proof_path)
            passed=passed and json.loads(proof_path.read_text())['passed']is True
        return dict(mode=mode,cpus=8,started=started,finished=time.time(),returncode=code,passed=passed,
                    folder=str(folder),receipt_sha256=file_sha(receipt_path)if receipt_path.exists()else None,
                    proof_sha256=file_sha(proof_path)if proof_path.exists()else None,
                    log_sha256=file_sha(folder/'group-child.log'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,specs))
    result=dict(schema='block-v1-native-diagnosis-group/1',passed=all(row['passed']for row in children),
                allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=parallel*8,memory_preflight=memory,
                children=children,scope='Parallel actual read-only DRC location and STA endpoint typing; no physical candidate repair or macro qualification')
    (out/'native-diagnosis-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Diagnostic child failed; independent peer completed and evidence preserved'
