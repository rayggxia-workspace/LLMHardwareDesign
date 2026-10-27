"""One implementation per M/V/R/S/T macro; older M8/VS are historical only."""
import json
from pathlib import Path


def vector_component(root,out,cpus,run,component):
    from io_slots import file_sha
    assert cpus==16 and component in ('group','function')
    folder=root/'project/rtl/block_library_v1';top='block_v1_v_'+component
    rtl=folder/(top+'.sv');bench=root/('project/experiments/block_v1/test_vector_'+component+'.cpp')
    run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module',top,'-I'+str(folder),'-Mdir',str(out/'obj'),str(rtl),str(bench)],component+'-build.log')
    run([str(out/('obj/V'+top))],component+'-result.json')
    result=json.loads((out/(component+'-result.json')).read_text());assert result['passed']
    result.update(source_sha256=file_sha(rtl),bench_sha256=file_sha(bench),physical_implementation_completed=False)
    (out/('five-macro-vector-'+component+'.json')).write_text(json.dumps(result,indent=2)+'\n')


def vector_latency(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    original=out.parents[2]/'block-v1-20261027-196/tasks/five-macro-vector-test'
    receipt=json.loads((original/'receipt.json').read_text());assert receipt['passed'] is True
    proof=original/'five-macro-vector-test.json';assert file_sha(proof)==receipt['outputs'][proof.name]
    tested=json.loads(proof.read_text());assert tested['passed']
    folder=root/'project/rtl/block_library_v1'
    assert all(file_sha(folder/name)==digest for name,digest in tested['source_sha256'].items())
    bench=root/'project/experiments/block_v1/test_vector_latency.cpp'
    driver=bench.with_name('test_vector_macro.cpp');assert file_sha(driver)==tested['bench_sha256']
    sources=[folder/name for name in ('block_v1_v.sv','block_v1_v_group.sv','block_v1_v_function.sv')]
    run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','16','-Wno-fatal',
         '--top-module','block_v1_v','-I'+str(folder),'-Mdir',str(out/'obj')]+list(map(str,sources))+[str(bench)],'latency-build.log')
    run([str(out/'obj/Vblock_v1_v')],'latency-result.json')
    result=json.loads((out/'latency-result.json').read_text());assert result['passed']
    result.update(source_sha256=tested['source_sha256'],scoreboard_receipt_sha256=file_sha(original/'receipt.json'),
                  driver_sha256=file_sha(driver),bench_sha256=file_sha(bench),physical_clock_qualified=False)
    (out/'five-macro-vector-latency.json').write_text(json.dumps(result,indent=2)+'\n')


def vector_test(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    folder=root/'project/rtl/block_library_v1'
    sources=[folder/name for name in ('block_v1_v.sv','block_v1_v_group.sv','block_v1_v_function.sv')]
    bench=root/'project/experiments/block_v1/test_vector_macro.cpp'
    run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module','block_v1_v','-I'+str(folder),'-Mdir',str(out/'obj')]+list(map(str,sources))+[str(bench)],'vector-build.log')
    run([str(out/'obj/Vblock_v1_v')],'vector-result.json')
    result=json.loads((out/'vector-result.json').read_text());assert result['passed'] and result['compose_cases']==270
    result.update(source_sha256={p.name:file_sha(p) for p in sources+[folder/'block_v1_v_tables.svh']},
                  bench_sha256=file_sha(bench),physical_implementation_completed=False,final_netlist_verified=False)
    (out/'five-macro-vector-test.json').write_text(json.dumps(result,indent=2)+'\n')


def vector_scan(root,out,cpus,run):
    assert cpus==16
    run(['python3',str(root/'project/experiments/block_v1/scan_vector_functions.py'),
         str(root/'project/rtl/block_library_v1/block_v1_v_tables.json')],'five-macro-vector-scan.json')
    assert json.loads((out/'five-macro-vector-scan.json').read_text())['passed']


def recurrent_test(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    rtl=root/'project/rtl/block_library_v1/block_v1_r.sv'
    bench=root/'project/experiments/block_v1/test_recurrent_macro.cpp'
    run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module','block_v1_r','-Mdir',str(out/'obj'),str(rtl),str(bench)],'recurrent-build.log')
    run([str(out/'obj/Vblock_v1_r')],'recurrent-result.json')
    result=json.loads((out/'recurrent-result.json').read_text())
    assert result['passed'] and result['random_recurrent_cases']==240 and result['conv_cases']==100
    result.update(source_sha256=file_sha(rtl),bench_sha256=file_sha(bench),physical_implementation_completed=False,final_netlist_verified=False)
    (out/'five-macro-recurrent-test.json').write_text(json.dumps(result,indent=2)+'\n')


def matrix_test(root, out, cpus, run):
    from io_slots import file_sha
    assert cpus == 16
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    rtl=root/'project/rtl/block_library_v1/block_v1_m.sv'
    bench=root/'project/experiments/block_v1/test_matrix_macro.cpp'
    run([compiler,'--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module','block_v1_m','-Mdir',str(out/'obj'),str(rtl),str(bench)],'matrix-build.log')
    run([str(out/'obj/Vblock_v1_m')],'matrix-result.json')
    result=json.loads((out/'matrix-result.json').read_text())
    assert result['passed'] and result['random_and_corner_tiles']==1200
    result.update(source_sha256=file_sha(rtl),bench_sha256=file_sha(bench),
                  physical_implementation_completed=False,final_netlist_verified=False)
    (out/'five-macro-matrix-test.json').write_text(json.dumps(result,indent=2)+'\n')


def map_matrix(root, out, cpus, run, top='block_v1_m'):
    from io_slots import file_sha
    assert cpus == 16
    assert top in ('block_v1_m','block_v1_s16k','block_v1_r','block_v1_v')
    rtl=root/('project/rtl/block_library_v1/'+top+'.sv')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    # Yosys scripts have their own tokenizer: Tcl braces are literal filename
    # characters here. All immutable server source paths are space-free.
    for path in (lib,rtl):assert not any(c.isspace() for c in str(path))
    script='read_liberty -lib '+str(lib)+'\nread_verilog -sv -I'+str(rtl.parent)+' '+str(rtl)+'\n'
    if top=='block_v1_v':
        for name in ('block_v1_v_group.sv','block_v1_v_function.sv'):
            script+='read_verilog -sv -I'+str(rtl.parent)+' '+str(rtl.parent/name)+'\n'
    if top=='block_v1_s16k':script+='read_verilog -sv '+str(root/'project/rtl/norm_service/store82.sv')+'\n'
    script+='hierarchy -check -top '+top+'\nsynth -top '+top+' -noabc\n'
    script+='dfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\ncheck -assert\n'
    script+='flatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty '+str(lib)+'\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (out/'map.ys').write_text(script);run(['yosys','-s',str(out/'map.ys')],'map.log')
    module=json.loads((out/'mapped.json').read_text())['modules'][top]
    cells={}
    for cell in module['cells'].values():
        kind=cell['type'];assert not kind.startswith('$'),kind
        cells[kind]=cells.get(kind,0)+1
    result=dict(passed=True,top=top,source_sha256=file_sha(rtl),liberty_sha256=file_sha(lib),
                mapped_sha256=file_sha(out/'mapped.v'),cells=cells,cell_count=sum(cells.values()),
                ports={k:dict(direction=v['direction'],bits=len(v['bits'])) for k,v in module['ports'].items()},
                physical_implementation_completed=False,functional_equivalence_qualified=False)
    label={'block_v1_m':'matrix','block_v1_s16k':'store','block_v1_r':'recurrent','block_v1_v':'vector'}[top]
    (out/('five-macro-'+label+'-map.json')).write_text(json.dumps(result,indent=2)+'\n')


def flatten_store(root,out,cpus,run):
    """Preserve successful187 cell mapping; flatten its wrapper without ABC rerun."""
    from io_slots import file_sha
    assert cpus==16
    source=out.parents[2]/'block-v1-20261027-187/tasks/five-macro-store-map'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] is True
    proof=source/'five-macro-store-map.json';assert file_sha(proof)==receipt['outputs'][proof.name]
    old=json.loads(proof.read_text());assert file_sha(source/'mapped.v')==old['mapped_sha256']
    assert file_sha(root/'project/rtl/block_library_v1/block_v1_s16k.sv')==old['source_sha256']
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    assert file_sha(lib)==old['liberty_sha256']
    script='read_liberty -lib '+str(lib)+'\nread_verilog '+str(source/'mapped.v')+'\n'
    script+='hierarchy -check -top block_v1_s16k\nflatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty '+str(lib)+'\n'
    script+='write_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (out/'flatten.ys').write_text(script);run(['yosys','-s',str(out/'flatten.ys')],'flatten.log')
    data=json.loads((out/'mapped.json').read_text());module=data['modules']['block_v1_s16k'];cells={}
    for c in module['cells'].values():
        kind=c['type'];assert not kind.startswith('$') and data['modules'][kind].get('attributes',{}).get('blackbox')
        cells[kind]=cells.get(kind,0)+1
    old.update(cells=cells,cell_count=sum(cells.values()),inventory_scope='Full flattened standard-cell leaf inventory including storage',
               mapped_sha256=file_sha(out/'mapped.v'),source_mapping_receipt_sha256=file_sha(source/'receipt.json'),
               source_mapping_report_sha256=file_sha(proof),abc_rerun=False)
    (out/'five-macro-store-map.json').write_text(json.dumps(old,indent=2)+'\n')


def store_test(root, out, cpus, run):
    from io_slots import file_sha
    assert cpus==16
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    sources=[root/'project/rtl/block_library_v1/block_v1_s16k.sv',root/'project/rtl/norm_service/store82.sv']
    bench=root/'project/experiments/block_v1/test_store_macro.cpp'
    run([compiler,'--cc','--exe','--build','-j',str(cpus),'-Wno-fatal',
         '--top-module','block_v1_s16k','-Mdir',str(out/'obj')]+list(map(str,sources))+[str(bench)],'store-build.log')
    run([str(out/'obj/Vblock_v1_s16k')],'store-result.json')
    result=json.loads((out/'store-result.json').read_text());assert result['passed'] and result['addresses']==1024
    result.update(source_sha256={str(p.relative_to(root)):file_sha(p) for p in sources},
                  bench_sha256=file_sha(bench),physical_implementation_completed=False,final_netlist_verified=False)
    (out/'five-macro-store-test.json').write_text(json.dumps(result,indent=2)+'\n')
