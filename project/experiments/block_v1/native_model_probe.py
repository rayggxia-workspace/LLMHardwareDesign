"""Actual sealed T6K timing-model export/readback diagnostic only.

This may inspect a producer whose independent physical receiver is unfinished.
Its diagnostic.lib is never a qualified macro view or a production view input.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from native_allocation_group import file_sha,memory_snapshot


def probe(root,out,cpus,run,policy):
    from io_slots import slot
    assert cpus==8 and policy in ('A','C')
    base=out.parents[2];top='transaction6k'
    pipeline=root/'project/experiments/block_v1/native_pipeline_viaonly.json'
    config=json.loads(pipeline.read_text())
    source=base/config['candidate_run']/('tasks/'+config['candidate_task_prefix']+top+'-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    assert receipt['mode']=='native-viaonly-run-transaction6k-'+policy.lower()
    report=source/'native-candidate.json';assert file_sha(report)==receipt['outputs'][report.name]
    producer=json.loads(report.read_text());assert producer['pipeline_completed']is True
    results=source/'flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base'
    inputs={}
    with slot(base):
        for name in ['6_final.odb','6_final.sdc','6_final.spef','6_final.v','6_final.def']:
            path=results/name;digest=file_sha(path)
            assert digest==receipt['outputs'][str(path.relative_to(source))]
            inputs[str(path)]=digest
    prep=base/config['preparation_run']/'tasks/native-prepare'
    bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    pins=prep/(top+'-'+policy)/'pins.json'
    assert file_sha(pins)==bound['outputs'][str(pins.relative_to(prep))]
    expected={p['pin']:p['direction'].lower()for p in json.loads(pins.read_text())['pins']}
    platform='/OpenROAD-flow-scripts/flow/platforms/nangate45'
    library='BV1_DIAGNOSTIC_'+policy;cell='T6K_DIAGNOSTIC_'+policy
    text='set_thread_count 8\nread_liberty {'+platform+'/lib/NangateOpenCellLibrary_typical.lib}\n'
    for command,name in [('read_db','6_final.odb'),('read_sdc','6_final.sdc'),('read_spef','6_final.spef')]:
        text+=command+' {'+str(results/name)+'}\n'
    text+='set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
    text+='write_timing_model -library_name '+library+' -cell_name '+cell+' diagnostic.lib\n'
    (out/'export.tcl').write_text(text)
    run(['openroad','-no_init','-exit','export.tcl'],'export.log')
    text='read_liberty diagnostic.lib\nset wanted_library {'+library+'}\nset wanted_master {'+cell+'}\n'
    text+='source {'+str(root/'project/experiments/block_v1/native_lib_pins.tcl')+'}\n'
    (out/'readback.tcl').write_text(text)
    run(['openroad','-no_init','-exit','readback.tcl'],'readback.log')
    observed={};prefix=library+'/'+cell+'/'
    for line in(out/'lib-interface.tsv').read_text().splitlines():
        name,direction=line.split('\t');assert name.startswith(prefix)
        pin=name[len(prefix):];assert pin not in observed
        if pin not in ('VDD','VSS'):observed[pin]=direction.lower()
    model=(out/'diagnostic.lib').read_text();types={}
    for kind in re.findall(r'\btiming_type\s*:\s*([a-zA-Z_]+)\s*;',model):types[kind]=types.get(kind,0)+1
    checks=dict(exact_non_pg_interface=observed==expected,nonempty_interface=bool(expected),
                clock_is_input=observed.get('clk')=='input',nonempty_timing_arcs=bool(types))
    with slot(base):assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    result=dict(schema='block-v1-native-timing-model-probe/1',passed=all(checks.values()),checks=checks,top=top,policy=policy,
                source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),producer_sha256=file_sha(report),inputs=inputs,
                pipeline_sha256=file_sha(pipeline),preparation_receipt_sha256=file_sha(prep/'receipt.json'),pins_sha256=file_sha(pins),
                lib_interface_script_sha256=file_sha(root/'project/experiments/block_v1/native_lib_pins.tcl'),
                diagnostic_model_sha256=file_sha(out/'diagnostic.lib'),diagnostic_model_bytes=(out/'diagnostic.lib').stat().st_size,
                pin_count=len(expected),timing_arc_types=types,physical_receiver_qualified=False,
                flat_abstract_boundary_qualified=False,exact_final_function_qualified=False,twelve_layer_qualified=False,qualified_hard_macro=False,
                scope='Read-only actual sealed T6K native STA timing-model API/export/interface diagnostic. No physical, boundary accuracy, input resistance, final-function, twelve-layer or macro qualification; diagnostic.lib cannot substitute for source-qualified views.')
    (out/'native-timing-model-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Actual diagnostic timing-model export/readback failed; preserve output'


def group(root,out,cpus):
    assert cpus==16
    memory=memory_snapshot()
    simultaneous=2 if memory['MemAvailable']>=2*32*1024**3*1.2 else 1
    def execute(policy):
        mode='native-timing-model-probe-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');started=time.time()
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'8'],
                                cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        receipt=folder/'receipt.json';proof=folder/'native-timing-model-probe.json'
        record=dict(mode=mode,cpus=8,started=started,finished=time.time(),returncode=code,passed=False)
        try:
            bound=json.loads(receipt.read_text());result=json.loads(proof.read_text())
            record.update(receipt_sha256=file_sha(receipt),proof_sha256=file_sha(proof))
            record['passed']=bool(code==0 and bound['passed']is True and bound['mode']==mode and bound['cpus']==8
                                  and bound['outputs'][proof.name]==file_sha(proof)and result['passed']is True and result['policy']==policy.upper())
        except(OSError,KeyError,ValueError)as error:record['validation_error']=repr(error)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-timing-model-probe-group/1',passed=all(c['passed']for c in children),children=children,
                allocated_cpus=cpus,simultaneous_workers=simultaneous,maximum_concurrent_cpu_ceilings=simultaneous*8,
                memory_preflight=memory,per_child_memory_estimate_bytes=32*1024**3,memory_safety_factor=1.2,
                qualified_hard_macro=False,scope='Two actual T6K timing-model export/readback diagnostics; no EDA physical or macro qualification')
    (out/'native-timing-model-probe-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'A diagnostic child failed; completed peer evidence retained'
