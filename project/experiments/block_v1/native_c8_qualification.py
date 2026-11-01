"""Complete repaired C8 receivers, two bounded children per c96 allocation.

The old full-graph replay is a prerequisite and never substitutes for a fresh
strict proof of the repaired physical source. No source edit or macro claim.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from io_slots import file_sha
from native_allocation_group import memory_snapshot


def replay_qualification(root,base):
    from native_c8_tie_lec import control
    qualified=control(root,base)
    folder=base/'block-v1-20261027-172/tasks/native-c8-tie-lec-group'
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] is True
    path=folder/'native-c8-tie-lec-group.json';assert file_sha(path)==receipt['outputs'][path.name]
    group=json.loads(path.read_text());assert group['passed'] is True
    assert len(group['children'])==2 and {c['policy']for c in group['children']}=={'a','c'}
    helper='project/experiments/block_v1/native_tie_projection.py'
    peers={}
    for child in group['children']:
        leaf=folder.parent/('native-c8-tie-lec-'+child['policy'])
        bound=json.loads((leaf/'receipt.json').read_text());assert child['passed'] is True and bound['passed'] is True
        assert child['receipt_sha256']==file_sha(leaf/'receipt.json')
        assert bound['inputs'][helper]==file_sha(root/helper)
        proof=leaf/'native-c8-tie-lec.json';assert file_sha(proof)==child['proof_sha256']==bound['outputs'][proof.name]
        p=json.loads(proof.read_text());assert p['passed'] is True and p['policy']==child['policy'].upper()
        assert p['control']==qualified and p['source_unchanged'] is True
        assert p['strict_native_lec']['passed'] is True and all(p['strict_native_lec']['checks'].values())
        assert p['original_rejected']['passed'] is False
        for name,digest in p['inputs'].items():assert file_sha(Path(name))==digest
        for name,key in [('strict-literal-kepler.log','strict_log_sha256'),('strict-literal-kepler.yml','strict_config_sha256')]:
            assert file_sha(leaf/name)==p[key]==bound['outputs'][name]
        for side,proof in p['constant_proofs'].items():
            q=Path(proof['path']);assert file_sha(q)==proof['sha256']==bound['outputs'][q.name]
            detail=json.loads(q.read_text());assert detail['passed'] is True and detail['exact_inverse_reconstruction'] is True
            assert detail['removed_count']==proof['removed_count']>0
            assert detail['emitted_structural_proof']['passed'] is True
        peers[child['policy']]=dict(receipt_sha256=file_sha(leaf/'receipt.json'),report_sha256=file_sha(leaf/'native-c8-tie-lec.json'))
    composition=composition_qualification(root,base)
    assert composition['binary_sha256']==qualified['binary_sha256'] and composition['library_sha256']==qualified['library_sha256']
    return dict(**qualified,composition_control=composition,complete_replay_receipt_sha256=file_sha(folder/'receipt.json'),
        complete_replay_report_sha256=file_sha(path),peers=peers,
        scope='Actual constant controls and complete old C8 positive strict replay; repaired final source must be proved again')


def composition_qualification(root,base):
    folder=base/'block-v1-20261027-173/tasks/native-projection-control-group'
    bound=json.loads((folder/'receipt.json').read_text());assert bound['passed'] is True
    path=folder/'native-projection-control-group.json';assert file_sha(path)==bound['outputs'][path.name]
    group=json.loads(path.read_text());assert group['passed'] is True
    assert len(group['children'])==2 and {c['polarity']for c in group['children']}=={0,1}
    binary=None;library=None
    for child in group['children']:
        leaf=folder.parent/('native-projection-control-'+str(child['polarity']))
        receipt=json.loads((leaf/'receipt.json').read_text());assert child['passed'] is True and receipt['passed'] is True
        assert child['receipt_sha256']==file_sha(leaf/'receipt.json')
        proof=leaf/'native-projection-control.json';assert file_sha(proof)==child['proof_sha256']==receipt['outputs'][proof.name]
        p=json.loads(proof.read_text());assert p['passed'] is True and p['polarity']==child['polarity']
        assert p['source_unchanged'] is True and len(p['unsupported_model_controls'])==2 and all(p['unsupported_model_controls'].values())
        assert p['results']['positive']['passed'] is True and all(p['results']['positive']['checks'].values())
        assert all(p['results'][name]['passed'] is False for name in ['wrong_tie','wrong_clock'])
        for name in ['native_logic_projection.py','native_tie_projection.py','structural_view.py','native_projection_control.py']:
            relative='project/experiments/block_v1/'+name;assert receipt['inputs'][relative]==file_sha(root/relative)
        binary=p['binary_sha256']if binary is None else binary;library=p['library_sha256']if library is None else library
        assert (binary,library)==(p['binary_sha256'],p['library_sha256'])
    return dict(receipt_sha256=file_sha(folder/'receipt.json'),report_sha256=file_sha(path),binary_sha256=binary,library_sha256=library)


def group(root,out,cpus):
    assert cpus==16
    base=out.parents[2];qualified=replay_qualification(root,base)
    pipeline=json.loads((root/'project/experiments/block_v1/native_pipeline_c8_escape.json').read_text())
    source=base/pipeline['candidate_run']/'tasks/native-c8-finish-group'
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed'] is True
    path=source/'native-escape-finish-group.json';assert file_sha(path)==bound['outputs'][path.name]
    finish=json.loads(path.read_text());assert finish['passed'] is True and len(finish['children'])==2
    assert {c['mode']for c in finish['children']}=={'native-c8-run-shared109-a','native-c8-run-shared109-c'}
    for child in finish['children']:
        assert child['passed'] is True and child['receipt_sha256']==file_sha(source.parent/child['mode']/'receipt.json')
    memory=memory_snapshot();budget=200*1024**3
    assert memory['MemAvailable']>=budget*1.2,'Insufficient available memory for one complete C8 receiver'
    parallel=2 if memory['MemAvailable']>=2*budget*1.2 else 1
    def execute(policy):
        mode='native-c8-receive-shared109-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);started=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'8'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-physical-receiver.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==8 and r['mode']==mode and file_sha(q)==r['outputs'][q.name]and json.loads(q.read_text())['passed'] is True
        return dict(policy=policy,mode=mode,cpus=8,started=started,finished=time.time(),returncode=code,passed=passed,
            receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    record=dict(schema='block-v1-native-c8-qualification-group/1',passed=all(c['passed']for c in children),children=children,
        allocated_cpus=cpus,simultaneous_workers=parallel,maximum_concurrent_cpu_ceilings=8*parallel,
        memory_preflight=memory,per_child_memory_budget_bytes=budget,parallel_memory_safety_factor=1.2,
        constant_control=qualified,source_finish_receipt_sha256=file_sha(source/'receipt.json'),
        exact_final_function_qualified=False,twelve_layer_qualified=False,qualified_hard_macro=False,
        scope='Fresh complete independent physical/STA/RC/PG/DRC/strict state-boundary LEC of repaired C8 source; full composed function and macro/twelve-layer qualification remain separate')
    (out/'native-c8-qualification-group.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Complete C8 receiver failed; all peer evidence retained'
