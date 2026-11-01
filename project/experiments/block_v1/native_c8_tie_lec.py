"""Repeat complete strict C8 LEC with audited literal tie functions.

Read the immutable failed graphs; no physical edit, no state cut removed and
no change to native_formal.inspect. A full positive correspondence is required.
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
from native_formal import inspect
from native_tie_projection import project
from structural_view import compare


def control(root,base):
    folder=base/'block-v1-20261027-171/tasks/native-tie-formal-control-group'
    r=json.loads((folder/'receipt.json').read_text());assert r['passed']is True
    path=folder/'native-tie-formal-control-group.json';assert file_sha(path)==r['outputs'][path.name]
    g=json.loads(path.read_text());assert g['passed']is True and {c['polarity']for c in g['children']}=={0,1}
    helper='project/experiments/block_v1/native_tie_projection.py';binary=None;library=None
    for c in g['children']:
        leaf=folder.parent/('native-tie-formal-control-'+str(c['polarity']))
        assert c['passed']is True and c['receipt_sha256']==file_sha(leaf/'receipt.json')
        accepted=json.loads((leaf/'receipt.json').read_text());assert accepted['passed']is True
        assert accepted['inputs'][helper]==file_sha(root/helper)
        proof=leaf/'native-tie-formal-control.json';assert file_sha(proof)==c['proof_sha256']==accepted['outputs'][proof.name]
        p=json.loads(proof.read_text());assert p['passed']is True and p['polarity']==c['polarity']
        assert p['results']['positive']['passed']is True and all(p['results']['positive']['checks'].values())
        assert all(p['results'][n]['passed']is False for n in ['original','wrong_tie','wrong_clock'])
        binary=p['binary_sha256']if binary is None else binary;library=p['library_sha256']if library is None else library
        assert (binary,library)==(p['binary_sha256'],p['library_sha256'])
    return dict(receipt_sha256=file_sha(folder/'receipt.json'),report_sha256=file_sha(path),binary_sha256=binary,library_sha256=library)


def verify(root,out,cpus,run,policy):
    assert cpus==2 and policy in 'AC';base=out.parents[2];qualified=control(root,base)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    assert file_sha(lib)==qualified['library_sha256']and file_sha(binary)==qualified['binary_sha256']
    source=base/'block-v1-20261027-134/tasks'/('native-receive-shared109-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is False
    original=source/'strict-projected-kepler.log';assert file_sha(original)==receipt['outputs'][original.name]
    old=inspect(original.read_text());assert old['passed']is False and old['checks']['no_unmatched_boundaries']is False
    inputs={str(original):file_sha(original)};proofs={};paths={}
    for label,side in [('before','0'),('after','1')]:
        path=source/('formal-'+label+'-logic.json');assert file_sha(path)==receipt['outputs'][path.name];inputs[str(path)]=file_sha(path)
        data=json.loads(path.read_text());converted,proof=project(data,lib.read_text())
        assert proof['removed_count']==old['counts']['diff'+side+' inputs']>0
        graph=out/(label+'-literal.json');graph.write_text(json.dumps(converted)+'\n');target=out/(label+'-literal.v');reparsed=out/(label+'-reparsed.json')
        ys='read_json '+str(graph)+'\nwrite_verilog -norename -noattr -noexpr '+str(target)+'\ndesign -reset\nread_liberty -lib '+str(lib)+'\nread_verilog '+str(target)+'\nhierarchy -check -top shared109\nwrite_json '+str(reparsed)+'\n'
        script=out/(label+'-emit.ys');script.write_text(ys);run(['yosys','-s',str(script)],label+'-emit.log')
        proof['emitted_structural_proof']=compare(converted,json.loads(reparsed.read_text()));proofs[label]=proof;paths[label]=target
        (out/(label+'-constant-proof.json')).write_text(json.dumps(proof,indent=2)+'\n')
        del data,converted,proof
    log=out/'strict-literal-kepler.log';config=out/'strict-literal-kepler.yml'
    config.write_text('format: verilog\ninput_paths:\n  - '+str(paths['before'])+'\n  - '+str(paths['after'])+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(log)+'\n')
    run([str(binary),'--config',str(config)],'strict-literal-command.log');received=inspect(log.read_text())
    unchanged=all(file_sha(Path(p))==h for p,h in inputs.items())
    record=dict(schema='block-v1-native-c8-tie-lec/1',passed=received['passed']and unchanged,policy=policy,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),inputs=inputs,original_rejected=old,
        control=qualified,constant_proofs={label:dict(path=str(out/(label+'-constant-proof.json')),sha256=file_sha(out/(label+'-constant-proof.json')),removed_count=p['removed_count'])for label,p in proofs.items()},
        strict_native_lec=received,strict_log_sha256=file_sha(log),strict_config_sha256=file_sha(config),source_unchanged=unchanged,
        physical_source_qualified=False,exact_final_function_qualified=False,qualified_hard_macro=False,
        scope='Complete immutable old C8 parsed graph strict LEC replay with real constant functions and exact inverse/emitted graph proofs; no physical source/DRC/function/macro qualification')
    (out/'native-c8-tie-lec.json').write_text(json.dumps(record,indent=2)+'\n');assert record['passed'],'Complete strict literal C8 LEC rejected; preserve all evidence'


def group(root,out,cpus):
    assert cpus==4;memory=memory_snapshot();budget=200*1024**3;assert memory['MemAvailable']>=budget*1.2
    parallel=2 if memory['MemAvailable']>=2*budget*1.2 else 1
    def execute(policy):
        mode='native-c8-tie-lec-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'2'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-c8-tie-lec.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==2 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=2,started=start,finished=time.time(),passed=passed,returncode=code,receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    record=dict(schema='block-v1-native-c8-tie-lec-group/1',passed=all(c['passed']for c in children),children=children,allocated_cpus=cpus,
        maximum_concurrent_cpu_ceilings=parallel*2,simultaneous_workers=parallel,memory_preflight=memory,per_child_memory_budget_bytes=budget,parallel_memory_safety_factor=1.2,qualified_hard_macro=False)
    (out/'native-c8-tie-lec-group.json').write_text(json.dumps(record,indent=2)+'\n');assert record['passed']
