"""Actual initialization and physical-contract controls share one allocation."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from io_slots import file_sha
from native_allocation_group import memory_snapshot


SPECS=[('native-composed-init-control',8,'native-composed-initialization.json'),
       ('native-composed-physical-control',1,'native-composed-physical-control.json')]


def qualified(root,base):
    folder=base/'block-v1-20261027-175/tasks/native-composed-controls-group'
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] is True
    report=folder/'native-composed-controls-group.json';assert file_sha(report)==receipt['outputs'][report.name]
    group=json.loads(report.read_text());assert group['passed'] is True
    assert len(group['children'])==2 and {c['mode']for c in group['children']}=={s[0]for s in SPECS}
    results={}
    for mode,cpus,name in SPECS:
        leaf=folder.parent/mode;child=next(c for c in group['children']if c['mode']==mode)
        bound=json.loads((leaf/'receipt.json').read_text());assert child['passed'] is True and bound['passed'] is True
        assert bound['mode']==mode and bound['cpus']==cpus and child['receipt_sha256']==file_sha(leaf/'receipt.json')
        path=leaf/name;assert file_sha(path)==child['proof_sha256']==bound['outputs'][name]
        p=json.loads(path.read_text());assert p['passed'] is True
        for helper in ['native_composed.py','native_composed_physical.py','native_composed_controls.py']:
            relative='project/experiments/block_v1/'+helper;assert bound['inputs'][relative]==file_sha(root/relative)
        if mode=='native-composed-init-control':
            assert p['module_sha256']==file_sha(root/'project/experiments/block_v1/native_composed.py')
            assert p['independently_connected_dff_inputs']==128 and p['missing_initialization_rejected']['returncode']==1
            assert p['observed_initial_words']['all-ones']==[0xffffffff]*4
        else:
            assert p['module_sha256']==file_sha(root/'project/experiments/block_v1/native_composed_physical.py')
            assert set(p['actual'])=={'A','C'} and all(v['positive']is True for v in p['actual'].values())
            assert len(p['rejected_faults'])==38 and all(v is True for v in p['rejected_faults'].values())
        results[mode]=dict(receipt_sha256=file_sha(leaf/'receipt.json'),report_sha256=file_sha(path))
    return dict(passed=True,group_receipt_sha256=file_sha(folder/'receipt.json'),group_report_sha256=file_sha(report),children=results)


def group(root,out,cpus):
    assert cpus==9
    memory=memory_snapshot();budget=32*1024**3;assert memory['MemAvailable']>=budget*1.2
    def execute(spec):
        mode,allocated,name=spec;folder=out.parent/mode;folder.mkdir(exist_ok=False);started=time.time()
        env=dict(os.environ,OMP_NUM_THREADS=str(allocated),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,str(allocated)],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/name;r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==allocated and r['mode']==mode and file_sha(q)==r['outputs'][name]and json.loads(q.read_text())['passed'] is True
        return dict(mode=mode,cpus=allocated,started=started,finished=time.time(),returncode=code,passed=passed,
            receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:children=list(pool.map(execute,SPECS))
    result=dict(schema='block-v1-native-composed-controls-group/1',passed=all(c['passed']for c in children),children=children,
        allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=9,memory_preflight=memory,
        combined_memory_estimate_bytes=budget,memory_safety_factor=1.2,qualified_hard_macro=False)
    (out/'native-composed-controls-group.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
