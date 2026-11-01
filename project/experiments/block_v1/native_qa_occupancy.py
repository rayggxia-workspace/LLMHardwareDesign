"""Run the pinned PR128 read-only native occupancy exporter under this budget."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from io_slots import file_sha,slot
from native_allocation_group import memory_snapshot
from native_views import received_contract


def export(root,out,cpus,run,policy):
    assert cpus==1 and policy in 'AC';base=out.parents[2]
    folder=base/'block-v1-20261027-164/tasks'/('native-escape-view-transaction6k-'+policy.lower())
    r=json.loads((folder/'receipt.json').read_text());assert r['passed']is True
    path=folder/'native-view-generation.json';assert file_sha(path)==r['outputs'][path.name]
    view=json.loads(path.read_text());assert view['passed']is True
    source=Path(view['source']);physical=Path(view['physical_receiver'])
    assert file_sha(source/'receipt.json')==view['source_receipt_sha256']
    assert file_sha(physical/'receipt.json')==view['physical_receiver_receipt_sha256']
    proof=physical/'native-physical-receiver.json';assert file_sha(proof)==view['physical_receiver_sha256']
    received_contract(json.loads(proof.read_text()),source,view['source_receipt_sha256'],'native_pipeline_escape.json','transaction6k',policy)
    odb=source/'flow/results/nangate45'/('bv1_transaction6k_'+policy)/'base/6_final.odb'
    expected=view['inputs'][str(odb)]
    with slot(base):assert file_sha(odb)==expected
    helper=root/'project/experiments/block_v1/odb_geometry.tcl'
    pinned=root/'project/experiments/block_v1/qa127_pinned';script=pinned/'source_occupancy.tcl'
    origin=json.loads((pinned/'origin.json').read_text());assert origin['source_commit']=='5eda23a0591a4c993ccdeaac8d221e736332d6fb'
    assert file_sha(script)==origin['sha256']=='ed9a3eec244097e238c52104332b3199be509cf05aefb425d1f5442f4463eade'
    inputs={str(p):file_sha(p)for p in [folder/'receipt.json',path,physical/'receipt.json',proof,helper,script]}
    text='set_thread_count 1\nset ::env(BV1QA_ODB) {'+str(odb)+'}\n'
    text+='set ::env(BV1QA_GEOMETRY_HELPER) {'+str(helper)+'}\nsource {'+str(script)+'}\n'
    (out/'readonly-occupancy.tcl').write_text(text)
    run(['openroad','-no_init','-exit','readonly-occupancy.tcl'],'native-occupancy.log')
    summary={}
    for line in(out/'occupancy-summary.tsv').read_text().splitlines():
        name,value=line.split('\t');assert name not in summary and value.isdigit();summary[name]=int(value)
    assert set(summary)=={'dbu_per_um','native_instances','native_master_obstruction_boxes'}
    assert summary['dbu_per_um']==2000 and summary['native_instances']>0
    target=out/'source-occupancy.tsv';assert target.stat().st_size>0
    assert all(file_sha(Path(p))==h for p,h in inputs.items())
    with slot(base):assert file_sha(odb)==expected
    report=dict(schema='block-v1-qa127-native-occupancy/1',passed=True,policy=policy,inputs=inputs,
        source_odb=str(odb),source_odb_sha256=expected,pinned_origin=origin,native_summary=summary,
        occupancy=dict(path=str(target),sha256=file_sha(target),bytes=target.stat().st_size),
        coverage_qualified=False,qualified_hard_macro=False,
        scope='Source-bound complete read-only actual ODB occupancy export using pinned PR128 tool; no geometry edit, OBS coverage/PG/model boundary acceptance remains independent')
    (out/'native-qa-occupancy.json').write_text(json.dumps(report,indent=2)+'\n')


def group(root,out,cpus):
    assert cpus==2;memory=memory_snapshot();budget=64*1024**3
    assert memory['MemAvailable']>=budget*1.2
    parallel=2 if memory['MemAvailable']>=2*budget*1.2 else 1
    def execute(policy):
        mode='native-qa-occupancy-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'1'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-qa-occupancy.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==1 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=1,started=start,finished=time.time(),passed=passed,returncode=code,
                    receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    report=dict(schema='block-v1-qa127-native-occupancy-group/1',passed=all(c['passed']for c in children),allocated_cpus=cpus,
        simultaneous_workers=parallel,maximum_concurrent_cpu_ceilings=parallel,memory_preflight=memory,
        per_child_memory_budget_bytes=budget,parallel_memory_safety_factor=1.2,children=children,qualified_hard_macro=False)
    (out/'native-qa-occupancy-group.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['passed'],'Read-only occupancy child failed; peer evidence retained'
