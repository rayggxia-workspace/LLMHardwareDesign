"""Behavioral acceptance of the exact routed T6K netlist, with real cell RAM.

Run the independent queue scoreboard against the unchanged physical final
Verilog. Random initial state is not a four-state or delay/STA qualification.
"""
import concurrent.futures
import json
from pathlib import Path


def receive_test(text):
    rows=[]
    for line in text.splitlines():
        try:value=json.loads(line)
        except ValueError:continue
        if isinstance(value,dict):rows.append(value)
    assert len(rows)==1,'Exactly one scoreboard result required'
    result=rows[0]
    assert result.get('passed')is True and result.get('seed')==1212026102
    assert result.get('transactions')==242
    for key in ['cycles','assertions']:
        assert type(result.get(key))is int and result[key]>0
    return result


def verify(root,out,cpus,run,policy,pipeline='native_pipeline_cap40.json'):
    from io_slots import file_sha,slot
    from native_formal import receive
    assert policy in ('A','C')and cpus>=8
    base=out.parents[2]
    assert pipeline in ('native_pipeline_cap40.json','native_pipeline_hold5.json','native_pipeline_diode.json','native_pipeline_diode_full.json','native_pipeline_viaonly.json','native_pipeline_escape.json')
    config=json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
    top='transaction6k'
    source=base/config['candidate_run']/('tasks/'+config['candidate_task_prefix']+top+'-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    prep=base/config['preparation_run']/'tasks/native-prepare'
    results=source/'flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base'
    netlist=results/'6_final.v'
    assert file_sha(netlist)==receipt['outputs'][str(netlist.relative_to(source))]
    diode=config.get('input_diode_master')=='ANTENNA_X1'
    formal=receive(source,receipt,results,top,prep,logic_context=(root,out,run)if diode else None)
    assert formal['passed']is True and formal['full_final_netlist_sha256']==file_sha(netlist)
    original_netlist_sha256=file_sha(netlist)
    if diode:
        view=formal['physical_functional_view'];assert view['passed']is True
        netlist=Path(view['full_view']);assert file_sha(netlist)==view['full_view_sha256']
    library=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    script='read_liberty -ignore_miss_func -ignore_miss_dir '+str(library)+'\nwrite_verilog -noattr cells.v\n'
    (out/'export-cells.ys').write_text(script)
    run(['yosys','-s','export-cells.ys'],'export-cells.log')
    verilator=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
    driver=root/'project/experiments/block_v1/test_transaction.cpp'
    threads=min(4,cpus//3)
    run([str(verilator),'--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module',top,'--prefix','Vtransaction6k','--Mdir',str(out/'obj'),
         '--output-split','12000','--output-split-cfuncs','150','--threads',str(threads),
         '--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O2',
         str(netlist),str(out/'cells.v'),str(driver)],'build-final.log')
    binary=out/'obj/Vtransaction6k';observed={}
    def simulate(case):
        name,initial,seed=case;log=name+'.log'
        run([str(binary),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],log)
        return name,dict(initial_mode=initial,runtime_seed=seed,scoreboard=receive_test((out/log).read_text()),
                         log_sha256=file_sha(out/log))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        observed=dict(pool.map(simulate,[('all-ones',1,121),('random-121',2,121),('random-122',2,122)]))
    assert all(row['scoreboard']==observed['all-ones']['scoreboard']for row in observed.values())
    with slot(base):
        assert file_sha(results/'6_final.v')==original_netlist_sha256
        assert file_sha(netlist)==(formal['physical_functional_view']['full_view_sha256']if diode else original_netlist_sha256)
    record=dict(schema='block-v1-native-final-function/1',passed=True,top=top,policy=policy,pipeline=pipeline,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
        final_netlist=str(netlist),final_netlist_sha256=file_sha(netlist),original_flow_netlist_sha256=original_netlist_sha256,formal=formal,
        liberty_sha256=file_sha(library),cell_models_sha256=file_sha(out/'cells.v'),
        driver_sha256=file_sha(driver),binary_sha256=file_sha(binary),initial_state_runs=observed,
        simultaneous_models=3,threads_per_model=threads,max_runtime_threads=3*threads,allocated_cpus=cpus,
        physical_receiver_qualified=False,flat_abstract_boundary_qualified=False,qualified_hard_macro=False,
        scope='Exact routed T6K zero-delay mapped-cell scoreboard with three initial-state configurations; no behavioral RAM replacement, four-state, delay/STA, complete C8 or macro-boundary qualification')
    (out/'native-final-function.json').write_text(json.dumps(record,indent=2)+'\n')
