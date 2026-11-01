"""Fresh whole-chip native DRC of immutable final C8 databases.

The route-stage report alone did not expose the T6K shorts discovered by157.
This independent gate checks actual final geometry, without route repair.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from io_slots import file_sha
from native_allocation_group import memory_snapshot


def verify(root,out,cpus,run,policy):
    assert cpus==8 and policy in ('A','C')
    source=out.parents[2]/'block-v1-20261027-128/tasks'/('native-run-shared109-'+policy.lower())
    r=json.loads((source/'receipt.json').read_text());assert r['passed']is True
    rel='flow/results/nangate45/bv1_shared109_'+policy+'/base/6_final.odb'
    database=source/rel;expected=r['outputs'][rel];assert file_sha(database)==expected
    script='set_thread_count 8\nread_db {%s}\nwrite_def before.def\n'%database
    script+='if {[llength [info commands ::drt::check_drc_cmd]] != 1} {error "Missing compiled native whole-chip checker"}\n'
    script+='set stream [open native-checker-api.txt w]\nputs $stream [info commands ::drt::*drc*]\n'
    script+='if {![catch {drt::check_drc_cmd} usage]} {error "Unexpected checker arity"}\nputs $stream $usage\nclose $stream\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
    (out/'native-whole-drc.tcl').write_text(script)
    run(['openroad','-no_init','-exit','native-whole-drc.tcl'],'native-whole-drc.log')
    assert 'drc_file x1 y1 x2 y2 marker_name'in(out/'native-checker-api.txt').read_text()
    report=out/'native-whole-drc.rpt';text=report.read_text()
    checks=dict(source_unchanged=file_sha(database)==expected,checker_geometry_unchanged=file_sha(out/'before.def')==file_sha(out/'after.def'),
                actual_final_full_chip_native_drc_zero=not text.strip())
    result=dict(schema='block-v1-native-whole-drc/1',passed=all(checks.values()),checks=checks,policy=policy,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),source_odb_sha256=expected,
        checker_command='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc',api_sha256=file_sha(out/'native-checker-api.txt'),
        report_sha256=file_sha(report),violations=text.count('violation type:'),categories={k:text.count('violation type: '+k+'\n')for k in sorted(set(re.findall(r'violation type: ([^\n]+)',text)))},
        report=text,qualified_hard_macro=False,scope='Fresh whole-chip native DRC on exact final C8 ODB with unchanged geometry; independent GDS/STA/function/PG/macro and twelve-layer gates still required')
    (out/'native-whole-drc.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Fresh actual final whole-chip native DRC failed; report retained'


def group(root,out,cpus):
    assert cpus==16
    memory=memory_snapshot();simultaneous=2 if memory['MemAvailable']>=2*200*1024**3*1.2 else 1
    def execute(policy):
        mode='native-whole-drc-c8-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'8'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-whole-drc.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==8 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=8,started=start,finished=time.time(),passed=passed,returncode=code,
                    receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-whole-drc-group/1',passed=all(r['passed']for r in children),allocated_cpus=cpus,
        simultaneous_workers=simultaneous,maximum_concurrent_cpu_ceilings=8*simultaneous,memory_preflight=memory,per_child_memory_budget_bytes=200*1024**3,
        children=children,qualified_hard_macro=False)
    (out/'native-whole-drc-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Actual C8 whole-chip native DRC child failed; independent peer evidence retained'
