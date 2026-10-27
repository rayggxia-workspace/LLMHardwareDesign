"""One implementation per M/V/R/S/T macro; older M8/VS are historical only."""
import json
from pathlib import Path


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
    assert top in ('block_v1_m','block_v1_s16k')
    rtl=root/('project/rtl/block_library_v1/'+top+'.sv')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    script='read_liberty -lib {'+str(lib)+'}\nread_verilog -sv {'+str(rtl)+'}\n'
    if top=='block_v1_s16k':script+='read_verilog -sv {'+str(root/'project/rtl/norm_service/store82.sv')+'}\n'
    script+='hierarchy -check -top '+top+'\nsynth -top '+top+' -noabc\n'
    script+='dfflibmap -liberty {'+str(lib)+'}\nabc -liberty {'+str(lib)+'}\nclean\ncheck -assert\n'
    script+='stat -liberty {'+str(lib)+'}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
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
    (out/('five-macro-'+('matrix' if top=='block_v1_m' else 'store')+'-map.json')).write_text(json.dumps(result,indent=2)+'\n')


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
